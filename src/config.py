import os

class SecretsConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'invalid_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://") or 'invalid_db_uri'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'supersecret')

class ValidationConfig:
    MAX_EMAIL_LEN = 120
    MAX_NAME_LEN = 100

class HostConfig:
    PORT = int(os.environ.get('PORT', 5555))