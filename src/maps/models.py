from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON, ARRAY
from ..extensions import db

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='maps', lazy=True)
    rating = db.relationship('Rating', backref='map', lazy=True)
    waypoints = db.relationship('Waypoint', backref='map', lazy=True, cascade="all, delete")

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "duration": str(self.duration) if self.duration else None,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat(),
            "rating": self.rating.serialize() if self.rating else None,
            "waypoints": [waypoint.serialize() for waypoint in self.waypoints]
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
    tags = db.Column(ARRAY(db.String), nullable=True)
    times_of_day = db.Column(JSON, nullable=True)  # JSON structure for time recommendations
    price = db.Column(db.Float, nullable=True, default=0.0)

    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'info': self.info,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'tags': self.tags,
            'times_of_day': self.times_of_day,
            'price': self.price
        }