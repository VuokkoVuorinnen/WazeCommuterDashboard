#!/bin/bash
echo "Main Script: Starting scheduler..."
# Start the scheduler in the background
python run.py --scheduler &

echo "Main Script: Starting Gunicorn..."
# Start Gunicorn
# Passing arguments from CMD in Dockerfile or defaults
# --log-level debug: More verbose logs
# --access-logfile -: Log access to stdout
# --error-logfile -: Log errors to stderr
# --capture-output: Capture stdout/stderr from workers
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --log-level debug --access-logfile - --error-logfile - --capture-output run:app
