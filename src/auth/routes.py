import base64
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from .models import User
from ..extensions import db
from ..maps.map_utils import validate_image
from ..maps.models import Map, format_duration

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.form
    image_files = request.files
    
    # Validate required fields
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    alias = data.get('alias')
    if not email or not password or not role:
        return jsonify({"error": "Email, password, and role are required"}), 400

    # Check if the email is already registered
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered"}), 409
    
    # Check if the alias is already registered
    if User.query.filter_by(alias=alias).first():
        return jsonify({"error": "Alias is already registered"}), 409
    
    profile_image = image_files.get('profile_image')
    image_data, error = validate_image(profile_image)
    if error and error != "No file uploaded.":
        return jsonify({"error": f"Error when retrieving map image: {error}"}),

    # Hash the password
    hashed_password = generate_password_hash(password, method='sha256')
    
    # Create new user
    new_user = User(
        email=email,
        password=hashed_password,
        role='traveler', # Deprecate this, no longer needed
        name=data.get('name'),
        bio=data.get('bio'),
        image_data=image_data,
        alias=alias
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully", "user_id": new_user.id}), 201

@auth_bp.route('/user/<int:user_id>/update', methods=['PATCH'])
@jwt_required()
def update_user_profile(user_id):
    current_user = get_jwt_identity()
    if current_user['id'] != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.form
    image_files = request.files

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Update alias if provided and not already taken by someone else
        new_alias = data.get('alias')
        if new_alias and new_alias != user.alias:
            if User.query.filter_by(alias=new_alias).first():
                return jsonify({"error": "Alias is already taken"}), 409
            user.alias = new_alias

        # Update name and bio
        user.name = data.get('name', user.name)
        user.bio = data.get('bio', user.bio)

        # Update profile image if provided
        profile_image = image_files.get('profile_image')
        if profile_image:
            image_data, error = validate_image(profile_image)
            if error:
                return jsonify({"error": f"Profile image error: {error}"}), 400
            user.image_data = image_data

        db.session.commit()
        return jsonify({"message": "User profile updated successfully", "user": user.serialize()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An error occurred while updating the profile", "details": str(e)}), 500

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
    access_token = create_access_token(identity={"email": user.email, "role": user.role, "id": user.id, "alias": user.alias},
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
        "alias": user.alias,
        "image_data": base64.b64encode(user.image_data).decode('utf-8') if user.image_data else None,
        "map_ids": user.map_ids
    })

@auth_bp.route('/user/<alias>', methods=['GET'])
def get_user_profile(alias):
    user = User.query.filter_by(alias=alias).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Dynamically fetch all maps where the user is the creator
    maps = Map.query.filter_by(creator_id=user.id).all()

    maps_metadata = [
        {
            "id": map.id,
            "title": map.title,
            "description": map.description,
            "duration": format_duration(map.duration),
            "rating": map.rating.average_rating if map.rating else None,
            "price": map.price,
            "countries": map.countries,
            "tags": map.tags,
            "image_data": base64.b64encode(map.image_data).decode('utf-8') if map.image_data else None
        }
        for map in maps
    ]

    # Serialize user data and add maps metadata
    user_data = user.serialize()
    user_data["maps"] = maps_metadata  # ✅ Fetch maps dynamically

    return jsonify(user_data), 200

