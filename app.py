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
    "update_interval": 300,
    "standard_commute_mins": 45
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
    "to_work": {"time_mins": 0, "distance_km": 0, "trend": "flat", "color": ""},
    "to_home": {"time_mins": 0, "distance_km": 0, "trend": "flat", "color": ""},
    "weather": {"temp": 0, "description": "--"},
    "traffic_alerts": [],
    "last_updated": "Initializing..."
}

logger = logging.getLogger('WazeRouteCalculator.WazeRouteCalculator')
logger.setLevel(logging.WARNING)

def calculate_traffic_color(current_time, standard_time):
    if standard_time == 0: return ""
    ratio = current_time / standard_time
    if ratio > 1.33: # > 33% longer (Red)
        return "heavy-traffic"
    elif ratio > 1.1: # > 10% longer (Orange)
        return "moderate-traffic"
    return ""

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
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=temperature_2m,apparent_temperature,weather_code"
        response = requests.get(url)
        data = response.json()
        temp = data['current']['temperature_2m']
        feels_like = data['current']['apparent_temperature']
        code = data['current']['weather_code']
        
        # WMO Weather code mapping with Emojis
        mapping = {
            0: ("Clear Sky", "☀️"), 1: ("Mainly Clear", "🌤️"), 2: ("Partly Cloudy", "⛅"), 3: ("Overcast", "☁️"),
            45: ("Foggy", "🌫️"), 48: ("Foggy", "🌫️"), 
            51: ("Drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Drizzle", "🌦️"),
            61: ("Rain", "🌧️"), 63: ("Rain", "🌧️"), 65: ("Rain", "🌧️"), 
            71: ("Snow", "❄️"), 73: ("Snow", "❄️"), 75: ("Snow", "❄️"),
            95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm", "⛈️"), 99: ("Thunderstorm", "⛈️")
        }
        
        desc, emoji = mapping.get(code, ("Cloudy", "☁️"))
        return round(temp), round(feels_like), desc, emoji
    except:
        return 0, 0, "--", ""

def get_traffic_alerts():
    try:
        response = requests.get("http://www.wegeninfo.be/rssnl.php", timeout=10)
        response.encoding = 'iso-8859-1'
        root = ET.fromstring(response.text)
        alerts = []
        for item in root.findall('.//item')[:10]: # Check more to ensure we get 5 good ones
            title = item.find('title').text
            if title and " - " in title:
                # Remove the timestamp prefix (e.g., "07-01-2026 | 12:32:27 - ")
                content = title.split(' - ', 1)[1].strip()
                
                # Clean up prefixes
                content = content.replace("FILE:", "Vertraging:").replace("ACTUA:", "").replace("VERKEER:", "").strip()
                
                # Filter out empty, too short, or meaningless tags
                if not content or len(content) < 3:
                    continue
                
                if content not in alerts:
                    alerts.append(content)
            
            if len(alerts) >= 5: break
            
        return alerts if alerts else ["Geen incidenten momenteel."]
    except Exception as e:
        print(f"Error fetching traffic alerts: {e}")
        return ["Kon verkeersinformatie niet ophalen."]

def calculate_trend(current, old, is_first_run):
    if is_first_run or current == 0 or old == 0:
        return "flat"
    if current > old:
        return "up"
    elif current < old:
        return "down"
    return "flat"

def update_data():
    while True:
        print(f"[{time.strftime('%H:%M:%S')}] Updating dashboard data...")
        is_first_run = current_status["last_updated"] == "Initializing..."
        std_time = CONFIG.get("standard_commute_mins", 45)
        
        # 1. Home -> Work
        t1, d1 = get_waze_route(HOME_ADDRESS, WORK_ADDRESS)
        trend1 = calculate_trend(t1, current_status["to_work"]["time_mins"], is_first_run)
        color1 = calculate_traffic_color(t1, std_time)
        current_status["to_work"] = {"time_mins": t1, "distance_km": d1, "trend": trend1, "color": color1}
        
        # 2. Work -> Home
        t2, d2 = get_waze_route(WORK_ADDRESS, HOME_ADDRESS)
        trend2 = calculate_trend(t2, current_status["to_home"]["time_mins"], is_first_run)
        color2 = calculate_traffic_color(t2, std_time)
        current_status["to_home"] = {"time_mins": t2, "distance_km": d2, "trend": trend2, "color": color2}
        
        # 3. Weather
        temp, feels, cond, emoji = get_weather()
        current_status["weather"] = {"temp": temp, "feels_like": feels, "description": cond, "emoji": emoji}
        
        # 4. Alerts
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
        :root {
            --bg-color: #121212;
            --card-bg: rgba(30, 30, 30, 0.65);
            --text-color: #ffffff;
            --accent-green: #32d74b;
            --accent-red: #ff453a;
            --accent-yellow: #ffcc00;
        }
        
        * { box-sizing: border-box; }

        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background: radial-gradient(circle at center, #1e2a3a 0%, #0d1117 100%);
            color: var(--text-color); 
            height: 100vh; 
            width: 100vw;
            margin: 0; 
            overflow: hidden; /* No scrolling */
            display: flex;
            flex-direction: column;
        }

        .container {
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr auto;
            gap: 1.5vh;
            padding: 1.5vh;
            width: 100%;
            height: 100%;
        }

        /* 4x1 Layout on very wide screens */
        @media (min-aspect-ratio: 2.5/1) {
            .container {
                grid-template-columns: 1fr 1fr 1fr 1fr;
                grid-template-rows: 1fr auto;
            }
        }

        /* 1x4 Layout on tall screens (Mobile Portrait) */
        @media (max-aspect-ratio: 3/4) {
            .container {
                grid-template-columns: 1fr;
                grid-template-rows: 1fr 1fr 1fr 1fr auto;
            }
            .card.wide {
                display: none;
            }
            .container {
                grid-template-rows: 1fr 1fr 1fr 1fr; /* No ticker row */
            }
        }

        .card {
            background-color: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            position: relative;
            padding: 0.5rem;
            min-height: 0; /* Important for grid overflow */
            min-width: 0;
        }

        .card.wide {
            grid-column: 1 / -1; /* Span all columns */
            flex-direction: row;
            justify-content: flex-start;
            padding: 0 1rem;
            height: 8vh; /* Fixed small height for ticker */
            min-height: 50px;
        }

        h1 { 
            font-size: 3.5vh; 
            color: #bbb; 
            text-transform: uppercase; 
            letter-spacing: 2px; 
            margin: 0 0 1vh 0; 
        }
        
        /* Dynamic font sizing using vh/vw to ensure fit */
        .big-value { 
            font-size: 11vh; 
            font-weight: 700; 
            line-height: 1; 
            color: #4cd964; 
            text-shadow: 0 2px 10px rgba(0,0,0,0.3); 
        }
        .big-value span { font-size: 4vh; font-weight: 400; color: #aaa; }
        .big-value.temp { color: #5ac8fa; }
        .big-value.time { color: #ffffff; font-variant-numeric: tabular-nums; }
        
        .details { 
            margin-top: 1vh; 
            font-size: 3vh; 
            color: #eee; 
        }
        
        .trend { font-size: 5vh; vertical-align: middle; }
        .trend.up { color: var(--accent-red); } 
        .trend.down { color: var(--accent-green); } 
        
        /* Ticker styles */
        .ticker-wrap {
            width: 100%;
            overflow: hidden;
            white-space: nowrap;
            mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
        }
        .ticker {
            display: inline-block;
            animation: ticker 60s linear infinite;
        }
        .ticker-item {
            display: inline-block;
            padding: 0 2rem;
            font-size: 2.5vh;
            color: var(--accent-yellow);
            line-height: 8vh; /* Center vertically in the fixed height bar */
        }
        @keyframes ticker {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        
        .footer { 
            position: absolute; 
            bottom: 5px; 
            right: 10px; 
            font-size: 0.8rem; 
            color: #444; 
            pointer-events: none;
        }
        
        .heavy-traffic { color: #ff3b30 !important; }
        .moderate-traffic { color: #ffcc00 !important; }

    </style>
    <script>
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('nl-BE', { hour: '2-digit', minute: '2-digit' });
            const dateStr = now.toLocaleDateString('nl-BE', { weekday: 'short', day: 'numeric', month: 'short' });
            document.getElementById('clock').textContent = timeStr;
            document.getElementById('date').textContent = dateStr;
        }
        setInterval(updateClock, 1000);
        window.onload = updateClock;
    </script>
</head>
<body>
    <div class="container">
        <!-- Tile 0: Clock -->
        <div class="card">
            <h1>Tijd & Datum</h1>
            <div class="big-value time" id="clock">00:00</div>
            <div class="details" id="date">Laden...</div>
        </div>

        <!-- Tile 1: Weather -->
        <div class="card">
            <h1>Weer</h1>
            <div class="big-value temp">
                {{ data.weather.emoji }} {{ data.weather.temp }}<span>°C</span>
            </div>
            <div class="details">
                {{ data.weather.description }}<br>
                <span style="font-size: 0.8em; color: #aaa;">Gevoel: {{ data.weather.feels_like }}°C</span>
            </div>
        </div>

        <!-- Tile 2: Home -> Work -->
        <div class="card">
            <h1>Home ➝ Work</h1>
            <div class="big-value {{ data.to_work.color }}">
                {{ data.to_work.time_mins }}<span>min</span>
                {% if data.to_work.trend == 'up' %}<span class="trend up">▲</span>{% endif %}
                {% if data.to_work.trend == 'down' %}<span class="trend down">▼</span>{% endif %}
            </div>
            <div class="details">{{ data.to_work.distance_km }} km</div>
        </div>

        <!-- Tile 3: Work -> Home -->
        <div class="card">
            <h1>Work ➝ Home</h1>
            <div class="big-value {{ data.to_home.color }}">
                {{ data.to_home.time_mins }}<span>min</span>
                {% if data.to_home.trend == 'up' %}<span class="trend up">▲</span>{% endif %}
                {% if data.to_home.trend == 'down' %}<span class="trend down">▼</span>{% endif %}
            </div>
            <div class="details">{{ data.to_home.distance_km }} km</div>
        </div>

        <!-- Tile 4: Traffic Alerts (Ticker) -->
        <div class="card wide">
            <h1 style="margin: 0; margin-right: 20px; white-space: nowrap; border-right: 2px solid #333; padding-right: 20px; font-size: 2vh;">Verkeer</h1>
            <div class="ticker-wrap">
                <div class="ticker">
                    {% if data.traffic_alerts %}
                        {% for alert in data.traffic_alerts %}
                        <div class="ticker-item">⚠️ {{ alert }}</div>
                        {% endfor %}
                    {% else %}
                        <div class="ticker-item" style="color: #4cd964;">Geen incidenten gemeld.</div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        Updated: {{ data.last_updated }}
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE, data=current_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)