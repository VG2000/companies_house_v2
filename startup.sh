#!/bin/bash

echo "Starting Django app..."

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files (if applicable)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# # Import data from a predefined zip file (optional)
# if [ -f /app/data/file.zip ]; then
#     echo "Importing data from file.zip..."
#     python manage.py import_csv /app/data/file.zip
# else
#     echo "No data file found to import."
# fi

# Start the Django development server
echo "Starting the development server..."
exec python manage.py runserver 0.0.0.0:8000
