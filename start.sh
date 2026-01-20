#!/bin/bash
# Start the scheduler in the background
python run.py --scheduler &

# Start Gunicorn
# Passing arguments from CMD in Dockerfile or defaults
exec gunicorn --bind 0.0.0.0:8000 --workers 2 run:app
