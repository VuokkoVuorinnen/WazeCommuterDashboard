# Waze Commuter Dashboard

A simple Flask-based dashboard that displays your commute time and distance using real-time Waze data.

## Setup Instructions

### 1. Create a Virtual Environment
It is recommended to use a virtual environment to manage dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Configure Your Address
Open `app.py` and fill in your destination address:
```python
# --- CONFIGURATION ---
FROM_ADDRESS = "Mediagenix, Dilbeek, Belgium"
TO_ADDRESS = "YOUR HOME ADDRESS HERE"
REGION = 'EU'
UPDATE_INTERVAL = 300  # Update Waze data every 5 minutes (300s)
# ---------------------
```

### 4. Run the Application
Start the Flask server:
```bash
python app.py
```

### 5. View the Dashboard
Open your web browser and navigate to:
[http://localhost:5000](http://localhost:5000)