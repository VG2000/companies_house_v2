# Use the official Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create a staticfiles directory
RUN mkdir -p /app/staticfiles

# Copy the Django project into the container
COPY . /app/

# Copy the startup script into the container
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Expose the app's port
EXPOSE 8000


