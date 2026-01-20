import threading
import time
import os
import sys
from app import create_app
from app.data_fetcher import data_store
from app.config import settings

app = create_app()

def run_update_loop():
    """Continuously updates the data in a background thread."""
    print("Scheduler: Starting update loop...")
    while True:
        try:
            data_store.update()
        except Exception as e:
            print(f"Scheduler: Error during update: {e}")
        time.sleep(settings.get("UPDATE_INTERVAL_SECS", 300))

if __name__ == '__main__':
    # Check for scheduler mode
    if "--scheduler" in sys.argv:
        run_update_loop()
    else:
        # Dev Mode: Run both updater and web server
        print("Performing initial data fetch...")
        try:
            data_store.update()
        except Exception as e:
            print(f"Initial update failed: {e}")

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
