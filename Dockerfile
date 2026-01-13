# Stage 1: Build the application with dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies if needed (e.g., for packages with C extensions)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# Stage 2: Create the final, lean production image
FROM python:3.12-slim

# Create a non-root user for security
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# Copy the installed dependencies from the builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy the application code
COPY . .

# Set the non-root user as the current user
USER app

# Expose the port Gunicorn will run on
EXPOSE 8000

# Use Gunicorn as the production WSGI server
# Bind to 0.0.0.0 to allow external connections.
# Use environment variables to configure workers for flexibility.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "run:app"]
