import time
import logging
import requests
import json
import os
import xml.etree.ElementTree as ET
import WazeRouteCalculator
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from app.config import settings

# Suppress noisy logging from the WazeRouteCalculator library
logging.getLogger('WazeRouteCalculator.WazeRouteCalculator').setLevel(logging.WARNING)

DATA_FILE = "dashboard_data.json"

class DataStore:
    """A thread-safe class to hold and update dashboard data using file storage."""

    def __init__(self):
        self.sp = None
        # Default state structure
        self.default_state = {
            "to_work": {"time_mins": 0, "distance_km": 0, "trend": "flat", "color": ""},
            "to_home": {"time_mins": 0, "distance_km": 0, "trend": "flat", "color": ""},
            "weather": {"temp": 0, "feels_like": 0, "description": "--", "emoji": ""},
            "traffic_alerts": [],
            "spotify": {"is_playing": False, "title": "", "artist": "", "cover_url": ""},
            "last_updated": "Initializing..."
        }

    @property
    def status(self):
        """Reads the current status from the JSON file."""
        if not os.path.exists(DATA_FILE):
            return self.default_state
        
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self.default_state

    def _init_spotify(self):
        """Initializes the Spotipy client if credentials are provided."""
        if self.sp:
            return self.sp

        if not settings.get("SPOTIFY_CLIENT_ID") or not settings.get("SPOTIFY_CLIENT_SECRET"):
            print("Spotify credentials not set. Skipping initialization.")
            return None
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=settings["SPOTIFY_CLIENT_ID"],
                client_secret=settings["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=settings["SPOTIFY_REDIRECT_URI"],
                scope="user-read-currently-playing",
                open_browser=False,
                cache_path=".spotify_cache"
            ))
            # The first call might trigger a token refresh or prompt
            self.sp.current_user()
            print("Spotify successfully initialized.")
            return self.sp
        except Exception as e:
            print(f"Spotify initialization failed. Please check your credentials and authorization. Error: {e}")
            return None

    def get_spotify_data(self):
        """Fetches the currently playing track from Spotify."""
        # Ensure client is initialized
        if not self.sp:
            self._init_spotify()
        
        if not self.sp:
            return {"is_playing": False, "title": "Not Configured", "artist": "", "cover_url": ""}
        try:
            current = self.sp.current_user_playing_track()
            if current and current.get('is_playing') and current.get('item'):
                item = current['item']
                return {
                    "is_playing": True,
                    "title": item['name'],
                    "artist": ", ".join(artist['name'] for artist in item['artists']),
                    "cover_url": item['album']['images'][0]['url'] if item['album']['images'] else ""
                }
        except Exception as e:
            # Handle token errors or other API issues gracefully
            print(f"Error fetching Spotify data: {e}")
        return {"is_playing": False, "title": "Not Playing", "artist": "", "cover_url": ""}

    @staticmethod
    def get_waze_route(start, end):
        """Calculates route time and distance using WazeRouteCalculator."""
        try:
            calculator = WazeRouteCalculator.WazeRouteCalculator(start, end, settings["WAZE_REGION"])
            time_mins, dist_km = calculator.calc_route_info()
            return int(time_mins), round(dist_km, 1)
        except Exception as e:
            print(f"Error fetching Waze route from {start} to {end}: {e}")
            return 0, 0

    @staticmethod
    def get_weather():
        """Fetches current weather from Open-Meteo."""
        try:
            lat, lon = settings["WEATHER_LAT"], settings["WEATHER_LONG"]
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,weather_code"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            temp = data['current']['temperature_2m']
            feels_like = data['current']['apparent_temperature']
            code = data['current']['weather_code']

            mapping = {
                0: ("Clear", "☀️"), 1: ("Clear", "🌤️"), 2: ("Cloudy", "⛅"), 3: ("Overcast", "☁️"),
                45: ("Fog", "🌫️"), 48: ("Fog", "🌫️"), 51: ("Drizzle", "🌦️"), 53: ("Drizzle", "🌦️"),
                55: ("Drizzle", "🌦️"), 61: ("Rain", "🌧️"), 63: ("Rain", "🌧️"), 65: ("Rain", "🌧️"),
                71: ("Snow", "❄️"), 73: ("Snow", "❄️"), 75: ("Snow", "❄️"), 95: ("Storm", "⛈️"),
                96: ("Storm", "⛈️"), 99: ("Storm", "⛈️")
            }
            desc, emoji = mapping.get(code, ("N/A", "🤷"))
            return round(temp), round(feels_like), desc, emoji
        except requests.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return 0, 0, "--", ""

    @staticmethod
    def get_traffic_alerts():
        """Fetches traffic alerts from wegeninfo.be RSS feed."""
        try:
            response = requests.get("http://www.wegeninfo.be/rssnl.php", timeout=10)
            response.encoding = 'iso-8859-1'
            root = ET.fromstring(response.text)
            alerts = []
            for item in root.findall('.//item/title')[:10]:
                if item.text and " - " in item.text:
                    content = item.text.split(' - ', 1)[1].strip()
                    content = content.replace("FILE:", "Vertraging:").replace("ACTUA:", "").strip()
                    if content and len(content) > 5 and content not in alerts:
                        alerts.append(content)
                if len(alerts) >= 5: break
            return alerts if alerts else ["Geen incidenten momenteel."]
        except Exception as e:
            print(f"Error fetching traffic alerts: {e}")
            return ["Kon verkeersinformatie niet ophalen."]

    @staticmethod
    def calculate_trend(current, old, is_first_run):
        if is_first_run or current == 0 or old == 0: return "flat"
        if current > old: return "up"
        if current < old: return "down"
        return "flat"

    @staticmethod
    def calculate_traffic_color(current_time, standard_time):
        if standard_time == 0: return ""
        ratio = current_time / standard_time
        if ratio > 1.33: return "heavy-traffic"
        if ratio > 1.1: return "moderate-traffic"
        return ""

    def update(self):
        """Fetches all data sources and updates the internal status."""
        print(f"[{time.strftime('%H:%M:%S')}] Updating dashboard data...")

        # Get current state for trend comparison
        current_state = self.status
        is_first_run = current_state["last_updated"] == "Initializing..."

        std_time = settings.get("STANDARD_COMMUTE_MINS", 45)

        # Waze Routes
        old_to_work = current_state["to_work"]["time_mins"]
        t1, d1 = self.get_waze_route(settings["HOME_ADDRESS"], settings["WORK_ADDRESS"])
        to_work_data = {
            "time_mins": t1, "distance_km": d1,
            "trend": self.calculate_trend(t1, old_to_work, is_first_run),
            "color": self.calculate_traffic_color(t1, std_time)
        }

        old_to_home = current_state["to_home"]["time_mins"]
        t2, d2 = self.get_waze_route(settings["WORK_ADDRESS"], settings["HOME_ADDRESS"])
        to_home_data = {
            "time_mins": t2, "distance_km": d2,
            "trend": self.calculate_trend(t2, old_to_home, is_first_run),
            "color": self.calculate_traffic_color(t2, std_time)
        }

        # Weather
        temp, feels, cond, emoji = self.get_weather()
        weather_data = {"temp": temp, "feels_like": feels, "description": cond, "emoji": emoji}

        # Alerts & Spotify
        alerts_data = self.get_traffic_alerts()
        spotify_data = self.get_spotify_data()

        new_state = {
            "to_work": to_work_data,
            "to_home": to_home_data,
            "weather": weather_data,
            "traffic_alerts": alerts_data,
            "spotify": spotify_data,
            "last_updated": time.strftime('%H:%M:%S')
        }

        # Atomic write
        temp_file = DATA_FILE + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(new_state, f)
        os.replace(temp_file, DATA_FILE)
        
        print("Update complete.")

# Global instance of the data store
data_store = DataStore()
