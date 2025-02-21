# Use official Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && apt-get clean

# Install Production Dependencies
COPY requirements.txt /app/requirements.txt
COPY requirements.prod.txt /app/requirements.prod.txt
RUN pip install --no-cache-dir -r requirements.prod.txt


# Copy Django project files
COPY . /app/

# Copy both startup scripts
COPY startup.dev.sh /app/startup.dev.sh
COPY startup.prod.sh /app/startup.prod.sh
RUN chmod +x /app/startup.dev.sh /app/startup.prod.sh

# Expose the app's port
EXPOSE 8080

# Run the selected startup script
CMD ["/bin/bash", "-c", "exec /app/startup.prod.sh"]

