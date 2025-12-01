# Use Python 3.11 slim image as base (smaller size, good for production)
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements file first (for better caching)
COPY requirements.txt .

# Install Python dependencies
# Note: We install all dependencies including test tools for completeness
# In production, you might want to create a separate requirements-prod.txt without test dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files to container
COPY . .

# Create directory for SQLite database if it doesn't exist
# The database will be created automatically when the app starts
RUN mkdir -p /app

# Expose port 5000 for Flask application
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Run the Flask application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

