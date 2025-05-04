from datetime import timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import Map, Rating, Waypoint
from ..extensions import db, logger
from ..users.services import get_current_user
from .map_utils import validate_base64_image, validate_image
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
                price=data.get('price', 0.0),
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
                    image_data=image_data,
                    country=wp.get('country', None)
                )
                db.session.add(waypoint)
            
            # Update the map's price/countrie based on the waypoints
            new_map.update_price_from_waypoints()
            new_map.update_countries_from_waypoints()

        # Commit the transaction
        db.session.commit()
        return jsonify({"message": "Map and waypoints created successfully", "map_id": new_map.id}), 201

    except Exception as e:
        db.session.rollback()
        logger.error("Error creating map and waypoints:", str(e))
        return jsonify({"error": "Failed to create map and waypoints", "details": str(e)}), 500

@maps_bp.route('/<int:map_id>/update_with_waypoints', methods=['PATCH'])
@jwt_required()
def update_map_with_waypoints(map_id):
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity['id']

    data = request.form
    image_files = request.files
    print("Files received:", request.files.keys())

    try:
        # Retrieve the map
        existing_map = Map.query.filter_by(id=map_id, creator_id=user_id).first()
        if not existing_map:
            return jsonify({"error": "Map not found or unauthorized"}), 404

        with db.session.begin_nested():
            # Update map fields
            existing_map.title = data.get('title', existing_map.title)
            existing_map.description = data.get('description', existing_map.description)
            existing_map.duration = data.get('duration') or existing_map.duration
            existing_map.price = float(data.get('price', existing_map.price))

            # Update map image if new one provided
            map_image = image_files.get('map_image')
            if map_image:
                image_data, error = validate_image(map_image)
                if error:
                    return jsonify({"error": f"Map image error: {error}"}), 400
                existing_map.image_data = image_data

            # Handle waypoints (optional - overwrite existing)
            waypoints_raw = data.get('waypoints')
            if waypoints_raw:
                waypoints = json.loads(waypoints_raw)

                # Clear existing waypoints
                Waypoint.query.filter_by(map_id=map_id).delete()

                # Add new waypoints
                for idx, wp in enumerate(waypoints):
                    image_file = image_files.get(f'waypoint_image_{idx}')
                    image_data = None
                    error = None
                    if image_file:
                        image_data, error = validate_image(image_file)
                    elif wp.get("image_data"):
                        image_data, error = validate_base64_image(wp["image_data"])
                    if error and error != "No file uploaded.":
                        return jsonify({"error": f"Waypoint {wp['title']} image error: {error}"}), 400

                    new_wp = Waypoint(
                        map_id=map_id,
                        title=wp['title'],
                        description=wp.get('description', ''),
                        info=wp.get('info', ''),
                        latitude=wp['latitude'],
                        longitude=wp['longitude'],
                        times_of_day=wp.get('times_of_day', {}),
                        price=wp.get('price', 0.0),
                        duration=wp.get('duration', None),
                        image_data=image_data,
                        country=wp.get('country', None),
                        city=wp.get('city', None)
                    )
                    db.session.add(new_wp)

                # Update map metadata based on new waypoints
                existing_map.update_price_from_waypoints()
                existing_map.update_countries_from_waypoints()

        db.session.commit()
        return jsonify({"message": "Map and waypoints updated successfully", "map_id": existing_map.id}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating map {map_id}: {str(e)}')
        return jsonify({"error": "Failed to update map and waypoints", "details": str(e)}), 500

@maps_bp.route('/<int:map_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_map(map_id):
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity['id']

    try:
        map_to_delete = Map.query.filter_by(id=map_id, creator_id=user_id).first()

        if not map_to_delete:
            return jsonify({"error": "Map not found or unauthorized"}), 404

        with db.session.begin_nested():
            # Delete associated waypoints and rating
            Waypoint.query.filter_by(map_id=map_id).delete()
            if map_to_delete.rating_id:
                Rating.query.filter_by(id=map_to_delete.rating_id).delete()

            # Delete the map itself
            db.session.delete(map_to_delete)

        db.session.commit()
        return jsonify({"message": "Map and associated waypoints deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting map {map_id}: {str(e)}")
        return jsonify({"error": "Failed to delete map", "details": str(e)}), 500


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
    try:
        # Retrieve filter values from query parameters
        price_param = request.args.get('price')       # Expected format: "20, 80"
        duration_param = request.args.get('duration')   # Expected format: "1, 10"
        rating_param = request.args.get('rating')       # Expected format: "1, 5"
        country_param = request.args.get('countries')     # Expected format: "USA", "Canada" or "" for no country
        city_param = request.args.get('cities')         # Expected format: "New York", "Toronto" or "" for no city
        tags_param = request.args.get('tags')           # Expected format: "tag1, tag2" or "" for no tags

        query = Map.query

        if 'creator_id' in request.args:
            try:
                query = query.filter(Map.creator_id == int(request.args['creator_id']))
            except ValueError:
                pass  # Log error if needed

        # Filter by price range if provided
        if price_param:
            try:
                low_price, high_price = [float(x.strip()) for x in price_param.split(',')]
                query = query.filter(Map.price >= low_price, Map.price <= high_price)
            except ValueError:
                pass  # Log error if needed

        # Filter by duration range if provided
        # Parse duration and convert to timedelta
        if duration_param:
            parts = [x.strip() for x in duration_param.split(',')]
            if len(parts) == 2:
                try:
                    low_duration = timedelta(days=float(parts[0]))
                    high_duration = timedelta(days=float(parts[1]))
                    query = query.filter(Map.duration >= low_duration).filter(Map.duration <= high_duration)
                except ValueError:
                    pass

        # Filter by rating range if provided TODO: Properly update ratings in the model
        # if rating_param:
        #     try:
        #         parsed = low_price, high_price = [float(x.strip()) for x in rating_param.split(',')]
        #         if parsed:
        #             low_rating, high_rating = parsed
        #             # Join the Rating table and filter on its 'score' column instead
        #             query = query.join(Rating).filter(Rating.average_rating >= low_rating).filter(Rating.average_rating <= high_rating)
        #     except ValueError:
        #         pass

        # Filter by country if provided
        if country_param:
            countries_list = [country.strip() for country in country_param.split(',')]
            query = query.filter(Map.countries.overlap(countries_list))

        # Filter by city if provided
        if city_param:
            cities_list = [city.strip() for city in city_param.split(',')]
            query = query.filter(Map.cities.overlap(cities_list))


        # Filter by tags if provided
        if tags_param:
            tags_list = [tag.strip() for tag in tags_param.split(',')]
            # Assuming Map.tags is stored as an ARRAY (or JSON) and your DB supports an "overlap" operator.
            query = query.filter(Map.tags.overlap(tags_list))
            # Adjust filtering if tags are stored differently

        maps = query.all()
        return jsonify([map.serialize() for map in maps]), 200

    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to fetch filtered maps", "details": str(e)}), 500



@maps_bp.route('/get_all_tags', methods=['GET'])
@jwt_required()
def get_all_tags():
    # Note: Not an efficient way to get list of valid tags, should make dedicated table for this
    try:
        # Query all tags from maps
        tags_query = Map.query.with_entities(Map.tags).all()

        # Flatten the list of tags and remove duplicates
        consolidated_tags = set()
        for tags in tags_query:
            if tags[0]:  # Ensure tags column is not null
                consolidated_tags.update(tags[0])  # Assume tags is stored as a list/array in JSON/ARRAY column

        return jsonify(sorted(consolidated_tags)), 200  # Sort the tags alphabetically
    except Exception as e:
        return jsonify({"error": "Failed to retrieve tags", "details": str(e)}), 500
