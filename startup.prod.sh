#!/bin/bash
set -e

echo "Starting Django in production mode..."

# Apply migrations (Only if needed)
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create a superuser for first time
echo "Creating first time superuser..."
python manage.py create_prod_superuser || true

# Populate SIC codes
echo "Populating SIC codes..."
python manage.py populate_sic || true

# Load data at startup
RUN python manage.py load_geodata || true

# Load postcodes
RUN python manage.py load_postcodes || true

# Start Gunicorn server
echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8080 companies_house.wsgi:application
