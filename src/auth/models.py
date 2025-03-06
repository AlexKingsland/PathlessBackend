import base64
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
    map_ids = db.Column(ARRAY(db.Integer), nullable=True, default=[])
    image_data = db.Column(db.LargeBinary, nullable=True)
    alias = db.Column(db.String(100), nullable=True) 

    def serialize(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "name": self.name,
            "bio": self.bio,
            "map_ids": self.map_ids,
            "image_data": base64.b64encode(self.image_data).decode('utf-8') if self.image_data else None,
            "alias": self.alias
        }