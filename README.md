# PathlessLandingBE
Backend for pathless landing page

# Schema Migration
1. flask db migrate -m "Added image_data field to Map model"
2. Check alembic migration file to check the changes are reflectiveof model updates
3. flask db upgrade
