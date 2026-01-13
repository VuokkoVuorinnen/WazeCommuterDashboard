import os
import json
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

class Config:
    """Base configuration settings."""

    # --- DEFAULT CONFIGURATION ---
    # These can be overridden by a config.json file or environment variables
    DEFAULT_CONFIG = {
        "WORK_ADDRESS": "Brussels, Belgium",
        "HOME_ADDRESS": "Antwerp, Belgium",
        "WAZE_REGION": "EU",
        "WEATHER_LAT": 51.2194,
        "WEATHER_LONG": 4.4025,
        "UPDATE_INTERVAL_SECS": 300,
        "STANDARD_COMMUTE_MINS": 45,
        "SPOTIFY_CLIENT_ID": "",
        "SPOTIFY_CLIENT_SECRET": "",
        "SPOTIFY_REDIRECT_URI": "https://127.0.0.1:8888/callback"
    }

    @staticmethod
    def load_user_config():
        """Loads configuration from config.json, allowing user overrides."""
        if not os.path.exists('config.json'):
            return {}
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config.json: {e}")
            return {}

    @classmethod
    def get_config(cls):
        """
        Builds the final configuration dictionary.
        Priority: Environment Variables > config.json > Defaults.
        """
        config = cls.DEFAULT_CONFIG.copy()
        user_config = cls.load_user_config()

        # Convert keys from snake_case in JSON to UPPER_CASE to match env vars
        user_config_upper = {key.upper(): value for key, value in user_config.items()}
        config.update(user_config_upper)

        # Environment variables take the highest priority
        for key in config:
            env_value = os.getenv(key)
            if env_value:
                # Attempt to cast to the same type as the default value
                default_value = cls.DEFAULT_CONFIG.get(key)
                if isinstance(default_value, int):
                    try:
                        config[key] = int(env_value)
                    except ValueError:
                        pass # Keep default if casting fails
                elif isinstance(default_value, float):
                    try:
                        config[key] = float(env_value)
                    except ValueError:
                        pass
                else:
                    config[key] = env_value

        return config

# Load the configuration once when the module is imported
settings = Config.get_config()
