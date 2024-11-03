from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..maps.models import Map
from ..extensions import db
from .services import get_current_user

user_bp = Blueprint('users', __name__)

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user = get_current_user()
    return jsonify(current_user.serialize()), 200

@user_bp.route('/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    data = request.get_json()
    current_user = get_current_user()

    # Update profile fields
    current_user.name = data.get('name', current_user.name)
    current_user.bio = data.get('bio', current_user.bio)

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200

@user_bp.route('/saved-maps', methods=['POST'])
@jwt_required()
def save_map():
    data = request.get_json()
    map_id = data.get('map_id')
    current_user = get_current_user()

    # Check if map exists
    map_ = Map.query.get(map_id)
    if not map_:
        return jsonify({"error": "Map not found"}), 404

    # Add map_id to user's saved maps if not already saved
    if map_id not in current_user.map_ids:
        current_user.map_ids.append(map_id)
        db.session.commit()
        return jsonify({"message": "Map saved successfully"}), 200
    else:
        return jsonify({"message": "Map is already saved"}), 200

@user_bp.route('/saved-maps', methods=['GET'])
@jwt_required()
def get_saved_maps():
    current_user = get_current_user()
    saved_maps = Map.query.filter(Map.id.in_(current_user.map_ids)).all()
    return jsonify([map.serialize() for map in saved_maps]), 200

@user_bp.route('/saved-maps/<int:map_id>', methods=['DELETE'])
@jwt_required()
def remove_saved_map(map_id):
    current_user = get_current_user()

    # Check if map_id is in user's saved maps
    if map_id in current_user.map_ids:
        current_user.map_ids.remove(map_id)
        db.session.commit()
        return jsonify({"message": "Map removed from saved maps"}), 200
    else:
        return jsonify({"error": "Map not found in saved maps"}), 404