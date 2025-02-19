from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from .models import User
from ..extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    if not email or not password or not role:
        return jsonify({"error": "Email, password, and role are required"}), 400

    # Check if the email is already registered
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered"}), 409

    # Hash the password
    hashed_password = generate_password_hash(password, method='sha256')
    
    # Create new user
    new_user = User(
        email=email,
        password=hashed_password,
        role='traveler', # Deprecate this, no longer needed
        name=data.get('name'),
        bio=data.get('bio')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully", "user_id": new_user.id}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Validate required fields
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Find the user by email
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Generate a JWT token
    access_token = create_access_token(identity={"email": user.email, "role": user.role, "id": user.id},
                                       expires_delta=timedelta(hours=24))
    
    return jsonify({"access_token": access_token, "user_id": user.id}), 200

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    # Get the current user's identity from the token
    current_user_identity = get_jwt_identity()
    user = User.query.filter_by(email=current_user_identity['email']).first()
    
    # Return the user's profile information
    return jsonify({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "bio": user.bio,
        "map_ids": user.map_ids
    })
