#!/bin/bash

echo "Starting Django app..."

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files (if applicable)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create a superuser for the Django admin
echo "Creating dev superuser..."
python manage.py create_dev_superuser

# Function to import_basic_company_data from a zip file
import_basic_company_data() {
    local zip_file=$1
    if [ -f "$zip_file" ]; then
        echo "Importing data from $zip_file..."
        python manage.py import_basic_company_data "$zip_file"
    else
        echo "No data file found: $zip_file"
    fi
}

# List of zip files to import
basic_company_data_zip_files=(
    # "/app/test_data/test.csv"
    # "/app/data/BasicCompanyData-2025-01-01-part1_7.zip"
    # "/app/data/BasicCompanyData-2025-01-01-part2_7.zip"
    # "/app/data/BasicCompanyData-2025-01-01-part3_7.zip"
    # "/app/data/BasicCompanyData-2025-01-01-part4_7.zip"
    # "/app/data/BasicCompanyData-2025-01-01-part5_7.zip"
    # "/app/data/BasicCompanyData-2025-01-01-part6_7.zip"
    # "/app/data/BasicCompanyData-2025-01-01-part7_7.zip"
)

# Loop through each zip file and import data
for zip_file in "${basic_company_data_zip_files[@]}"; do
    import_basic_company_data "$zip_file"
done

# Function to import monthly data from a zip file
import_monthly_data() {
    local zip_file=$1
    if [ -f "$zip_file" ]; then
        echo "Importing data from $zip_file..."
        python manage.py import_monthly_data "$zip_file"
    else
        echo "No data file found: $zip_file"
    fi
}

# List of zip files to import
monthly_zip_files=(
    # "/app/test_data/html.zip"
# "/app/data/Accounts_Monthly_Data-January2024.zip"
# "/app/data/Accounts_Monthly_Data-February2024.zip"
# "/app/data/Accounts_Monthly_Data-March2024.zip"
# "/app/data/Accounts_Monthly_Data-April2024.zip"
# "/app/data/Accounts_Monthly_Data-May2024.zip"
# "/app/data/Accounts_Monthly_Data-June2024.zip"
# "/app/data/Accounts_Monthly_Data-July2024.zip"
# "/app/data/Accounts_Monthly_Data-August2024.zip"
# "/app/data/Accounts_Monthly_Data-September2024.zip"
# "/app/data/Accounts_Monthly_Data-October2024.zip"
# "/app/data/Accounts_Monthly_Data-November2024.zip"
# "/app/data/Accounts_Monthly_Data-December2024.zip"
)

# Loop through each zip file and import data
for zip_file in "${monthly_zip_files[@]}"; do
    import_monthly_data "$zip_file"
done

# Start the Django development server
echo "Starting the development server..."
exec python manage.py runserver 0.0.0.0:8000
