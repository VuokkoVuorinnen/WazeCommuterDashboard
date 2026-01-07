# Waze Commuter Dashboard

A smart, "glanceable" dashboard for your morning routine. Displays real-time commute times via Waze, local weather conditions, traffic alerts, and a live clock. Designed to run on a Raspberry Pi or any always-on display.

## Features

*   **Commute Times:** Real-time travel time and distance for Home ➝ Work and Work ➝ Home using Waze data.
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
    "weather_long": 4.3517
}
```
*Note: `config.json` is git-ignored to keep your personal data private.*

### 4. Run the Application
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
