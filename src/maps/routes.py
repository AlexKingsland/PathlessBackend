from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Map, Rating, Waypoint
from ..extensions import db, logger
from ..users.services import get_current_user
from .map_utils import validate_image
import random
import json

maps_bp = Blueprint('maps', __name__)

@maps_bp.route('/create_with_waypoints', methods=['POST'])
@jwt_required()
def create_map_with_waypoints():
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity['id']

    data = request.form
    image_files = request.files
    print("Files received:", request.files.keys())

    
    try:
        # Start a transaction block
        with db.session.begin_nested():
            # Create a new Rating object
            rating = Rating()
            db.session.add(rating)

            # Get individual waypoint tags to aggregate them over the map
            waypoints = json.loads(data.get('waypoints', []))
            map_tags = []
            for wp in waypoints:
                map_tags += wp.get('tags', [])

            # Get map image if exists
            map_image = image_files.get('map_image')
            image_data, error = validate_image(map_image)
            if error and error != "No file uploaded.":
                return jsonify({"error": f"Error when retrieving map image: {error}"}),

            # Create a new Map object
            new_map = Map(
                title=data['title'],
                description=data.get('description', ''),
                duration=data.get('duration') if data.get('duration') else None,
                creator_id=user_id,
                rating=rating,
                tags=map_tags,
                image_data=image_data
            )
            db.session.add(new_map)
            db.session.flush()  # Get the new_map ID before committing

            # Add waypoints to the new map
            for idx, wp in enumerate(waypoints):
                image_file = image_files.get(f'waypoint_image_{idx}')  # Get image for this waypoint
                image_data, error = validate_image(image_file)

                if error and error != "No file uploaded.":
                    return jsonify({"error": f"Waypoint {wp['title']}: {error}"}),
                waypoint = Waypoint(
                    map_id=new_map.id,
                    title=wp['title'],
                    description=wp.get('description', ''),
                    info=wp.get('info', ''),
                    latitude=wp['latitude'],
                    longitude=wp['longitude'],
                    times_of_day=wp.get('times_of_day', {}),
                    price=wp.get('price', 0.0),
                    duration=wp.get('duration') if wp.get('duration') else None,
                    image_data=image_data
                )
                db.session.add(waypoint)

        # Commit the transaction
        db.session.commit()
        return jsonify({"message": "Map and waypoints created successfully", "map_id": new_map.id}), 201

    except Exception as e:
        db.session.rollback()
        logger.error("Error creating map and waypoints:", str(e))
        return jsonify({"error": "Failed to create map and waypoints", "details": str(e)}), 500

@maps_bp.route('/create_map', methods=['POST'])
@jwt_required()
def create_map():
    # Retrieve the current user's identity
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity['id']

    data = request.form
    
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


@maps_bp.route('/<int:map_id>', methods=['GET'])
def get_map(map_id):
    map = Map.query.get_or_404(map_id)
    return jsonify(map.serialize()), 200

@maps_bp.route('/<int:map_id>/waypoints', methods=['POST'])
@jwt_required()
def add_waypoint(map_id):
    data = request.form
    current_user = get_current_user()
    map_ = Map.query.get_or_404(map_id)

    # Ensure only the map creator can add waypoints
    if map_.creator_id != current_user.id:
        return jsonify({"error": "Only the creator of this map can add waypoints"}), 403
    
    # Image Handling
    image = request.files.get('image')
    image_data, error = validate_image(image)

    if error:
        return jsonify({"error": error}), 400

    waypoint = Waypoint(
        map_id=map_id,
        title=data['title'],
        description=data.get('description', ''),
        info=data.get('info', ''),
        latitude=data['latitude'],
        longitude=data['longitude'],
        tags=data.get('tags', []),
        times_of_day=data.get('times_of_day', {}),
        price=data.get('price', 0.0),
        image_data=image_data
    )
    db.session.add(waypoint)
    db.session.commit()

    return jsonify({"message": "Waypoint added successfully", "waypoint_id": waypoint.id}), 201

@maps_bp.route('/<int:map_id>/rate', methods=['POST'])
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

@maps_bp.route('/<int:map_id>/waypoints', methods=['GET'])
def get_waypoints(map_id):
    map = Map.query.get_or_404(map_id)
    waypoints = [waypoint.serialize() for waypoint in map.waypoints]
    return jsonify(waypoints)

@maps_bp.route('/<int:map_id>', methods=['GET'])
@jwt_required()
def get_map_with_waypoints(map_id):
    map = Map.query.get_or_404(map_id)
    return jsonify(map.serialize()), 200

@maps_bp.route('/get_all_maps_with_waypoints', methods=['GET'])
@jwt_required()
def get_all_maps_with_waypoints():
    # Query all maps from the database
    maps = Map.query.all()

    # Serialize each map along with its waypoints
    maps_with_waypoints = [map.serialize() for map in maps]

    return jsonify(maps_with_waypoints), 200

@maps_bp.route('/get_filtered_maps_with_waypoints', methods=['GET'])
@jwt_required()
def get_filtered_maps_with_waypoints():
    # Start building the query
    query = Map.query

    # Dynamically apply filters based on query parameters
    if 'title' in request.args:
        query = query.filter(Map.title.ilike(f"%{request.args['title']}%"))  # Case-insensitive partial match

    if 'creator_id' in request.args:
        query = query.filter(Map.creator_id == int(request.args['creator_id']))

    if 'min_price' in request.args:
        query = query.filter(Map.price >= float(request.args['min_price']))

    if 'max_price' in request.args:
        query = query.filter(Map.price <= float(request.args['max_price']))

    if 'duration' in request.args:
        query = query.filter(Map.duration == request.args['duration'])

    if 'tags' in request.args:
        try:
            tags = json.loads(request.args.get('tags', '[]'))
            query = query.filter(Map.tags.contains(tags))  # Assumes tags is stored as a JSON/ARRAY column
        except ValueError:
            pass  # Ignore invalid tags

    # Fetch the query results
    maps = query.all()

    # Randomize and limit the results if max_size is specified
    max_size = int(request.args.get('max_size', 0))
    if max_size > 0 and max_size < len(maps):
        maps = random.sample(maps, max_size)

    # Serialize the maps and their waypoints
    maps_with_waypoints = [map.serialize() for map in maps]

    return jsonify(maps_with_waypoints), 200
