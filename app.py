import time
import threading
import logging
import requests
import json
import os
import xml.etree.ElementTree as ET
from flask import Flask, render_template_string
import WazeRouteCalculator
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)

# --- CONFIGURATION ---
DEFAULT_CONFIG = {
    "work_address": "Brussels, Belgium",
    "home_address": "Antwerp, Belgium",
    "weather_lat": 51.2194,
    "weather_long": 4.4025,
    "region": "EU",
    "update_interval": 300,
    "standard_commute_mins": 45,
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "spotify_redirect_uri": "https://127.0.0.1:8888/callback"
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
    "spotify": {"is_playing": False, "title": "", "artist": "", "cover_url": ""},
    "last_updated": "Initializing..."
}

logger = logging.getLogger('WazeRouteCalculator.WazeRouteCalculator')
logger.setLevel(logging.WARNING)

# Spotify Client (Global)
sp = None

def init_spotify():
    global sp
    if not CONFIG["spotify_client_id"] or not CONFIG["spotify_client_secret"]:
        print("Spotify credentials not set. Skipping.")
        return

    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CONFIG["spotify_client_id"],
            client_secret=CONFIG["spotify_client_secret"],
            redirect_uri=CONFIG["spotify_redirect_uri"],
            scope="user-read-currently-playing",
            open_browser=False,
            cache_path=".spotify_cache"
        ))
        # Trigger internal token check/prompt immediately
        sp.current_user_playing_track()
        print("Spotify successfully initialized.")
    except Exception as e:
        print(f"Spotify initialization failed: {e}")

def get_spotify_data():
    global sp
    if sp is None:
         return {"is_playing": False, "title": "Not Configured", "artist": "", "cover_url": ""}

    try:
        current = sp.current_user_playing_track()
        if current and current.get('is_playing'):
            item = current['item']
            if item:
                return {
                    "is_playing": True,
                    "title": item['name'],
                    "artist": ", ".join(artist['name'] for artist in item['artists']),
                    "cover_url": item['album']['images'][0]['url'] if item['album']['images'] else ""
                }
    except Exception as e:
        print(f"Error fetching Spotify data: {e}")
    
    return {"is_playing": False, "title": "Not Playing", "artist": "", "cover_url": ""}

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
        
        # 5. Spotify
        current_status["spotify"] = get_spotify_data()
        
        current_status["last_updated"] = time.strftime('%H:%M:%S')
        time.sleep(UPDATE_INTERVAL)

if __name__ == '__main__':
    # Initialize Spotify before starting threads/server to allow CLI interaction
    init_spotify()
    
    thread = threading.Thread(target=update_data)
    thread.daemon = True
    thread.start()
    
    app.run(host='0.0.0.0', port=5000)