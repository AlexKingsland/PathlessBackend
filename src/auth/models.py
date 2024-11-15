from flask import jsonify
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY
from ..extensions import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=True)
    name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    map_ids = db.Column(ARRAY(db.Integer), nullable=True, default=[])  # List of map IDs associated with the user

    def serialize(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "name": self.name,
            "bio": self.bio,
            "map_ids": self.map_ids
        }