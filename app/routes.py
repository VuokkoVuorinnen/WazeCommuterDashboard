from flask import render_template
from flask import current_app as app
from .data_fetcher import data_store

@app.route('/')
def dashboard():
    """Renders the main dashboard page."""
    return render_template('index.html', data=data_store.status)
