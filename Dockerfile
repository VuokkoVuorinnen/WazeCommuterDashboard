# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.12-slim

# Set the working directory to /app
WORKDIR /app

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Install system dependencies (none currently needed for our pure-python deps, 
# but kept here if we need to add things like 'git' or 'gcc' later)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for the Flask app
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
