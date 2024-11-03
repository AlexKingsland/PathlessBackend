from flask_jwt_extended import get_jwt_identity
from ..auth.models import User

def get_current_user() -> User:
    identity = get_jwt_identity()
    return User.query.filter_by(email=identity['email']).first()