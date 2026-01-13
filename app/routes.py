from flask import render_template
from flask import current_app as app
from .data_fetcher import data_store
from datetime import datetime

def get_commute_mode(current_time=None):
    """
    Determines the commute mode based on the current time.
    Morning (00:00 - 10:00): to_work
    Afternoon (10:01 - 23:59): to_home
    """
    if current_time is None:
        current_time = datetime.now()

    # Check if time is before 10:01 AM
    # 10:00:59 is still <= 10:00 AM.
    # We want to switch at 10:01:00.
    if current_time.hour < 10 or (current_time.hour == 10 and current_time.minute == 0):
        return "to_work"
    return "to_home"

@app.route('/')
def dashboard():
    """Renders the main dashboard page."""
    commute_mode = get_commute_mode()
    return render_template('index.html', data=data_store.status, commute_mode=commute_mode)
