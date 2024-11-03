from flask import Flask
from src.config import SecretsConfig
from flask_cors import CORS
from .extensions import db, jwt, migrate
from .auth.routes import auth_bp
from .maps.routes import maps_bp
from .users.routes import user_bp

# Register DB models
from .auth.models import User
from .maps.models import Map, Waypoint, Rating

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(SecretsConfig)

    # Allow cross origin calls
    CORS(app, support_credentials=True)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Create the database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(maps_bp, url_prefix='/maps')
    app.register_blueprint(user_bp, url_prefix='/users')

    return app