import time
import threading
import logging
import requests
import json
import os
import xml.etree.ElementTree as ET
from flask import Flask, render_template_string
import WazeRouteCalculator

app = Flask(__name__)

# --- CONFIGURATION ---
DEFAULT_CONFIG = {
    "work_address": "Brussels, Belgium",
    "home_address": "Antwerp, Belgium",
    "weather_lat": 51.2194,
    "weather_long": 4.4025,
    "region": "EU",
    "update_interval": 300
}

def load_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return config

CONFIG = load_config()

WORK_ADDRESS = CONFIG["work_address"]
HOME_ADDRESS = CONFIG["home_address"]
REGION = CONFIG["region"]
LATITUDE = CONFIG["weather_lat"]
LONGITUDE = CONFIG["weather_long"]
UPDATE_INTERVAL = CONFIG["update_interval"]
# ---------------------

current_status = {
    "to_work": {"time_mins": 0, "distance_km": 0},
    "to_home": {"time_mins": 0, "distance_km": 0},
    "weather": {"temp": 0, "description": "--"},
    "traffic_alerts": [],
    "last_updated": "Initializing..."
}

logger = logging.getLogger('WazeRouteCalculator.WazeRouteCalculator')
logger.setLevel(logging.WARNING)

def get_waze_route(start, end):
    try:
        calculator = WazeRouteCalculator.WazeRouteCalculator(start, end, REGION)
        route_time, route_dist = calculator.calc_route_info()
        return int(route_time), round(route_dist, 1)
    except Exception as e:
        print(f"Error fetching Waze route: {e}")
        return 0, 0

def get_weather():
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=temperature_2m,weather_code"
        response = requests.get(url)
        data = response.json()
        temp = data['current']['temperature_2m']
        code = data['current']['weather_code']
        
        mapping = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Foggy", 48: "Foggy", 51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
            61: "Rain", 63: "Rain", 65: "Rain", 71: "Snow", 73: "Snow", 75: "Snow",
            95: "Thunderstorm"
        }
        return round(temp), mapping.get(code, "Cloudy")
    except:
        return 0, "--"

def get_traffic_alerts():
    try:
        # Federal Police Traffic Info RSS
        response = requests.get("http://www.wegeninfo.be/rssnl.php", timeout=10)
        # Handle encoding
        response.encoding = 'iso-8859-1'
        root = ET.fromstring(response.text)
        alerts = []
        for item in root.findall('.//item')[:5]: # Get top 5
            title = item.find('title').text
            if title:
                # Clean up title (remove date/time prefix for cleaner look)
                clean_title = title.split('-', 1)[-1].strip() if '-' in title else title
                alerts.append(clean_title)
        return alerts
    except Exception as e:
        print(f"Error fetching traffic alerts: {e}")
        return ["Could not fetch alerts"]

def update_data():
    while True:
        print(f"[{time.strftime('%H:%M:%S')}] Updating dashboard data...")
        t1, d1 = get_waze_route(HOME_ADDRESS, WORK_ADDRESS)
        current_status["to_work"] = {"time_mins": t1, "distance_km": d1}
        
        t2, d2 = get_waze_route(WORK_ADDRESS, HOME_ADDRESS)
        current_status["to_home"] = {"time_mins": t2, "distance_km": d2}
        
        temp, cond = get_weather()
        current_status["weather"] = {"temp": temp, "description": cond}
        
        current_status["traffic_alerts"] = get_traffic_alerts()
        
        current_status["last_updated"] = time.strftime('%H:%M:%S')
        time.sleep(UPDATE_INTERVAL)

thread = threading.Thread(target=update_data)
thread.daemon = True
thread.start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Commute Dashboard</title>
    <meta http-equiv="refresh" content="300">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background-color: #121212; 
            color: #ffffff; 
            height: 100vh; 
            margin: 0; 
            display: flex; 
            flex-direction: column;
            justify-content: center; 
            align-items: center; 
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        #clock { font-size: 5rem; font-weight: 700; margin: 0; color: #fff; }
        #date { font-size: 1.5rem; color: #888; margin-top: -10px; }

        .container {
            display: grid;
            grid-template-columns: repeat(2, 400px);
            grid-template-rows: repeat(2, 300px);
            gap: 25px;
        }
        .card {
            background-color: #1e1e1e;
            padding: 30px;
            border-radius: 24px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        h1 { font-size: 1rem; color: #888; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 15px; }
        
        .big-value { font-size: 5.5rem; font-weight: 700; line-height: 1; color: #4cd964; }
        .big-value span { font-size: 1.8rem; font-weight: 400; color: #888; }
        .big-value.temp { color: #5ac8fa; }
        
        .details { margin-top: 15px; font-size: 1.4rem; color: #ddd; }
        
        /* Alerts Styling */
        .alerts-list { text-align: left; font-size: 0.95rem; color: #ffcc00; list-style: none; padding: 0; margin-top: 10px; }
        .alerts-list li { margin-bottom: 8px; border-left: 3px solid #ffcc00; padding-left: 10px; }

        .footer { margin-top: 40px; font-size: 0.9rem; color: #444; }
        
        .heavy-traffic { color: #ff3b30 !important; }
    </style>
    <script>
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('nl-BE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const dateStr = now.toLocaleDateString('nl-BE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
            document.getElementById('clock').textContent = timeStr;
            document.getElementById('date').textContent = dateStr;
        }
        setInterval(updateClock, 1000);
        window.onload = updateClock;
    </script>
</head>
<body>
    <div class="header">
        <div id="clock">00:00:00</div>
        <div id="date">Laden...</div>
    </div>

    <div class="container">
        <!-- Tile 1: Home -> Work -->
        <div class="card">
            <h1>Home ➝ Work</h1>
            <div class="big-value {% if data.to_work.time_mins > 45 %}heavy-traffic{% endif %}">
                {{ data.to_work.time_mins }}<span>min</span>
            </div>
            <div class="details">{{ data.to_work.distance_km }} km</div>
        </div>

        <!-- Tile 2: Work -> Home -->
        <div class="card">
            <h1>Work ➝ Home</h1>
            <div class="big-value {% if data.to_home.time_mins > 45 %}heavy-traffic{% endif %}">
                {{ data.to_home.time_mins }}<span>min</span>
            </div>
            <div class="details">{{ data.to_home.distance_km }} km</div>
        </div>

        <!-- Tile 3: Weather -->
        <div class="card">
            <h1>Weer</h1>
            <div class="big-value temp">
                {{ data.weather.temp }}<span>°C</span>
            </div>
            <div class="details">{{ data.weather.description }}</div>
        </div>

        <!-- Tile 4: Traffic Alerts -->
        <div class="card" style="justify-content: flex-start;">
            <h1>Verkeersinfo</h1>
            <ul class="alerts-list">
                {% for alert in data.traffic_alerts %}
                <li>{{ alert }}</li>
                {% endfor %}
            </ul>
        </div>
    </div>

    <div class="footer">
        Laatste update: {{ data.last_updated }}
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE, data=current_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE, data=current_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
