#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting Django in development mode..."

# Apply migrations
echo "Applying migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create a superuser for development
echo "Creating dev superuser..."
python manage.py create_dev_superuser || true

# Populate SIC codes
echo "Populating SIC codes..."
python manage.py load_sic_data || true

# Load company data - Only use on db rebuild. Have an update button in the UI 
# echo "Populating Company table..."
# python manage.py load_company_data || true

# # # Load data at startup
echo "Loading geodata..."
python manage.py load_uk_geodata || true

# # Load postcodes
echo "Loading postcodes..."
python manage.py load_postcodes || true

# Start Django development server
echo "Starting development server..."
exec python manage.py runserver 0.0.0.0:8000 --noreload
