# Waze Commuter Dashboard

A smart, "glanceable" dashboard for your morning routine. Displays real-time commute times via Waze, local weather conditions, traffic alerts, and a live clock. Designed to run on a Raspberry Pi or any always-on display.

## Features

*   **Commute Times:** Real-time travel time and distance for Home ➝ Work and Work ➝ Home using Waze data.
*   **Spotify Now Playing:** Shows the currently playing track and album art (replaces Work ➝ Home tile).
*   **Weather:** Current temperature and conditions (via Open-Meteo).
*   **Traffic News:** Live traffic alerts and incidents from the Belgian Federal Police (Wegeninfo.be).
*   **Live Clock:** Large, easy-to-read clock and date.
*   **Visual Alerts:** Traffic times turn red when commute is longer than 45 minutes.

## Setup Instructions

### 1. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration
Copy the example configuration file and add your details:
```bash
cp config.example.json config.json
```
Edit `config.json`:
```json
{
    "home_address": "Your Home Address, City, Country",
    "work_address": "Your Work Address, City, Country",
    "weather_lat": 50.8503,
    "weather_long": 4.3517,
    "standard_commute_mins": 45,
    "spotify_client_id": "YOUR_SPOTIFY_CLIENT_ID",
    "spotify_client_secret": "YOUR_SPOTIFY_CLIENT_SECRET",
    "spotify_redirect_uri": "https://localhost:8888/callback"
}
```
*   `standard_commute_mins`: Your typical commute time in minutes. Used to calculate traffic severity colors (Orange > 10% delay, Red > 33% delay).
*   `weather_lat` / `weather_long`: Coordinates for your local weather (find them on Google Maps).

### 4. Spotify Configuration
To enable the "Now Playing" feature:
1.  Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2.  Create a new App.
3.  In the App settings, add `https://localhost:8888/callback` to the **Redirect URIs**.
4.  Copy your **Client ID** and **Client Secret** into your `config.json`.
5.  **First Run:** When you start the application, check the console output. It may ask you to visit a URL to authorize access. Open that URL in a browser logged into your Spotify account. After authorizing, you will be redirected to a page that might fail to load (because it's localhost) - this is normal. Copy the URL from your address bar (which contains the code) and paste it back into the console if prompted, or the application might handle it automatically if you have a local server running. *Note: Running this locally on your desktop first to generate the `.spotify_cache` file is recommended before deploying to a headless device like a Raspberry Pi.*

### 5. Run the Application
Start the Flask server:
```bash
python app.py
```

### 5. View the Dashboard
Open your web browser and navigate to:
[http://localhost:5000](http://localhost:5000)

## Customization
*   **Refresh Rate:** The dashboard auto-refreshes data every 5 minutes. You can change `UPDATE_INTERVAL` in `app.py`.
*   **Traffic Threshold:** Adjust the logic in the HTML template to change the "heavy traffic" color threshold (default is > 45 mins).
