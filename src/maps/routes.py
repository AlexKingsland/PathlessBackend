from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Map, Rating
from ..extensions import db
from ..users.services import get_current_user

maps_bp = Blueprint('maps', __name__)

@maps_bp.route('/maps', methods=['POST'])
@jwt_required()
def create_map():
    # Retrieve the current user's identity
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity['id']

    data = request.get_json()
    
    # Create a new Rating object but don't commit it to the database yet
    rating = Rating()
    db.session.add(rating)

    # Create a new Map object with the rating and creator_id set
    new_map = Map(
        title=data['title'],
        description=data.get('description', ''),
        duration=data.get('duration'),
        creator_id=user_id,
        rating=rating  # Assign the rating object directly
    )
    db.session.add(new_map)
    db.session.commit()  # Commit both the map and the rating in one transaction

    return jsonify({"message": "Map created successfully", "map_id": new_map.id}), 201


@maps_bp.route('/maps/<int:map_id>', methods=['GET'])
def get_map(map_id):
    map = Map.query.get_or_404(map_id)
    return jsonify(map.serialize()), 200

@maps_bp.route('/maps/<int:map_id>/waypoints', methods=['POST'])
@jwt_required()
def add_waypoint(map_id):
    data = request.get_json()
    current_user = get_current_user()
    map_ = Map.query.get_or_404(map_id)

    # Ensure only the map creator can add waypoints
    if map_.creator_id != current_user.id:
        return jsonify({"error": "Only the creator of this map can add waypoints"}), 403

    waypoint = Waypoint(
        map_id=map_id,
        title=data['title'],
        description=data.get('description', ''),
        info=data.get('info', ''),
        latitude=data['latitude'],
        longitude=data['longitude'],
        tags=data.get('tags', []),
        times_of_day=data.get('times_of_day', {}),
        price=data.get('price', 0.0)
    )
    db.session.add(waypoint)
    db.session.commit()

    return jsonify({"message": "Waypoint added successfully", "waypoint_id": waypoint.id}), 201

@maps_bp.route('/maps/<int:map_id>/rate', methods=['POST'])
@jwt_required()
def rate_map(map_id):
    data = request.get_json()
    rating_value = data.get('rating')
    if not (0 <= rating_value <= 5):
        return jsonify({"error": "Rating must be between 0 and 5"}), 400

    map_ = Map.query.get_or_404(map_id)
    rating = map_.rating
    if not rating:
        return jsonify({"error": "Rating entity not found for this map"}), 404

    rating.update_rating(rating_value)
    db.session.commit()

    return jsonify(rating.serialize()), 200

@maps_bp.route('/maps/<int:map_id>/waypoints', methods=['GET'])
def get_waypoints(map_id):
    map = Map.query.get_or_404(map_id)
    waypoints = [waypoint.serialize() for waypoint in map.waypoints]
    return jsonify(waypoints)
