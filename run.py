import threading
import time
import os
from app import create_app
from app.data_fetcher import data_store
from app.config import settings

app = create_app()

def run_update_loop():
    """Continuously updates the data in a background thread."""
    while True:
        data_store.update()
        time.sleep(settings.get("UPDATE_INTERVAL_SECS", 300))

if __name__ == '__main__':
    # It's crucial to perform the first data fetch *before* starting the web server.
    # This ensures that the dashboard has data on the very first load.
    # The Spotify client also needs its first run in the main thread for potential
    # user interaction (copy-pasting auth URL).
    print("Performing initial data fetch...")
    data_store.update()

    # Start the background thread for continuous updates
    update_thread = threading.Thread(target=run_update_loop)
    update_thread.daemon = True
    update_thread.start()

    # This check is for Gunicorn, which uses the __name__ == 'main' block
    # We let Gunicorn handle the web server execution.
    if os.environ.get("GUNICORN_WORKERS"):
        # The app object is automatically picked up by Gunicorn
        pass
    else:
        # Run the Flask development server if not using Gunicorn
        app.run(host='0.0.0.0', port=5000)
