import time
import threading
import logging
from flask import Flask, render_template_string
import WazeRouteCalculator

app = Flask(__name__)

# --- CONFIGURATION ---
FROM_ADDRESS = "Mediagenix, Dilbeek, Belgium"
TO_ADDRESS = "FILL YOUR ADDRESS IN HERE"
REGION = 'EU'
UPDATE_INTERVAL = 300  # Update Waze data every 5 minutes (300s)
# ---------------------

# Global variable to store the latest data
current_status = {
    "time_mins": 0,
    "distance_km": 0,
    "last_updated": "Initializing..."
}

# Configure logging to hide spammy Waze logs
logger = logging.getLogger('WazeRouteCalculator.WazeRouteCalculator')
logger.setLevel(logging.WARNING)

def fetch_waze_data():
    """Runs in the background to fetch data every X minutes."""
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Fetching route from Waze...")
            calculator = WazeRouteCalculator.WazeRouteCalculator(FROM_ADDRESS, TO_ADDRESS, REGION)
            route_time, route_dist = calculator.calc_route_info()
            
            # Update the global variable
            current_status["time_mins"] = int(route_time)
            current_status["distance_km"] = round(route_dist, 1)
            current_status["last_updated"] = time.strftime('%H:%M:%S')
            
            print(f"[{time.strftime('%H:%M:%S')}] Success: {int(route_time)} mins")
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            current_status["last_updated"] = "Error fetching data"
        
        time.sleep(UPDATE_INTERVAL)

# Start the background thread
thread = threading.Thread(target=fetch_waze_data)
thread.daemon = True # Ensures thread dies when you close the script
thread.start()

# HTML Template stored inside the script for simplicity
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Home Dashboard</title>
    <meta http-equiv="refresh" content="300">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background-color: #1a1a1a; 
            color: #ffffff; 
            height: 100vh; 
            margin: 0; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
        }
        .card {
            background-color: #2d2d2d;
            padding: 50px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            min-width: 300px;
        }
        h1 { font-size: 1.2rem; color: #888; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 20px; }
        .time { font-size: 7rem; font-weight: 700; line-height: 1; color: #4cd964; }
        .time span { font-size: 2rem; font-weight: 400; color: #888; }
        .details { margin-top: 20px; font-size: 1.5rem; color: #ddd; }
        .footer { margin-top: 40px; font-size: 0.9rem; color: #555; }
        
        /* Change color if traffic is bad (simple logic: > 45 mins) */
        .heavy-traffic { color: #ff3b30; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Mediagenix ➝ Home</h1>
        
        <div class="time {% if data.time_mins > 45 %}heavy-traffic{% endif %}">
            {{ data.time_mins }}<span>min</span>
        </div>
        
        <div class="details">{{ data.distance_km }} km</div>
        
        <div class="footer">
            Updated at {{ data.last_updated }}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE, data=current_status)

if __name__ == '__main__':
    # Host 0.0.0.0 allows you to view this on your phone if on the same Wifi
    app.run(host='0.0.0.0', port=5000)
