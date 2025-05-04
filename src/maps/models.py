from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON, ARRAY
from ..extensions import db
import base64
import re

# Preload the regex pattern as a global variable for efficiency
DURATION_REGEX = re.compile(r'(?:(\d+) days?, )?(\d+):(\d+):(\d+)')

class Rating(db.Model):
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    average_rating = db.Column(db.Float, default=0.0)
    num_ratings = db.Column(db.Integer, default=0)

    def serialize(self):
        return {
            "id": self.id,
            "average_rating": self.average_rating,
            "num_ratings": self.num_ratings
        }

    def update_rating(self, new_rating):
        total_score = self.average_rating * self.num_ratings
        self.num_ratings += 1
        self.average_rating = round((total_score + new_rating) / self.num_ratings, 2)

class Map(db.Model):
    __tablename__ = 'maps'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration = db.Column(db.Interval, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    rating_id = db.Column(db.Integer, db.ForeignKey('ratings.id', ondelete='SET NULL'))
    tags = db.Column(ARRAY(db.String), nullable=True)
    image_data = db.Column(db.LargeBinary, nullable=True)  # Store image as binary data
    price = db.Column(db.Float, nullable=True, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    countries = db.Column(ARRAY(db.String(255)), nullable=True, default=[])
    cities = db.Column(ARRAY(db.String(255)), nullable=True, default=[])
    
    creator = db.relationship('User', backref='maps', lazy=True)
    rating = db.relationship('Rating', backref='map', lazy=True)
    waypoints = db.relationship('Waypoint', backref='map', lazy=True, cascade="all, delete")

    def update_price_from_waypoints(self):
        """
        Updates the Map's price attribute to be the sum of the price attributes of all its waypoints.
        Assumes each waypoint has a 'price' attribute.
        """
        self.price = sum(
            waypoint.price for waypoint in self.waypoints if waypoint.price is not None
        )

    def update_countries_from_waypoints(self):
        """
        Updates the Map's countries attribute to be a list of unique country names from all its waypoints.
        Assumes each waypoint has a 'country' attribute.
        """
        self.countries = list(
            set(waypoint.country for waypoint in self.waypoints if waypoint.country is not None)
        )

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "duration": format_duration(self.duration),
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat(),
            "rating": self.rating.serialize() if self.rating else None,
            "price": self.price,
            'tags': self.tags,
            'countries': self.countries,
            'cities': self.cities,
            "waypoints": [waypoint.serialize() for waypoint in self.waypoints],
            'image_data': base64.b64encode(self.image_data).decode('utf-8') if self.image_data else None,
            "creator": self.creator.serialize() if self.creator else None
        }

class Waypoint(db.Model):
    __tablename__ = 'waypoints'
    
    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer, db.ForeignKey('maps.id', ondelete='CASCADE'))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    info = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    times_of_day = db.Column(JSON, nullable=True)  # JSON structure for time recommendations
    price = db.Column(db.Float, nullable=True, default=0.0)
    rating = db.Column(db.Float, nullable=True, default=0.0)
    duration = db.Column(db.Interval, nullable=True)
    image_data = db.Column(db.LargeBinary, nullable=True)  # Store image as binary data
    country = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(255), nullable=True)

    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'info': self.info,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'times_of_day': self.times_of_day,
            'price': self.price,
            'duration': format_duration(self.duration),
            'image_data': base64.b64encode(self.image_data).decode('utf-8') if self.image_data else None,
            'country': self.country,
            'city': self.city,
        }
    

def format_duration(duration):
    if not duration:
        return None

    # Use the preloaded regex pattern to match the duration format
    match = DURATION_REGEX.match(str(duration))
    if match:
        days = match.group(1)
        hours = match.group(2)
        minutes = match.group(3)

        # Build the formatted string
        formatted_duration = []
        if days and int(days) > 0:
            formatted_duration.append(f"{days} day{'s' if int(days) > 1 else ''}")
        
        if int(hours) > 0:
            formatted_duration.append(f"{hours} hour{'s' if int(hours) > 1 else ''}")
        
        if int(minutes) > 0:
            formatted_duration.append(f"{minutes} minute{'s' if int(minutes) > 1 else ''}")

        return ', '.join(formatted_duration)

    # If the format doesn't match, return the original duration string
    return str(duration)