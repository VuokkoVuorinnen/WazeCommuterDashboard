import unittest
import os
import json
import time
from app.data_fetcher import DataStore, DATA_FILE

class TestDataPersistence(unittest.TestCase):
    def setUp(self):
        # Clean up any existing data file before test
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        self.store = DataStore()

    def tearDown(self):
        # Clean up after test
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)

    def test_default_status(self):
        """Test that status returns defaults when no file exists."""
        status = self.store.status
        self.assertEqual(status["last_updated"], "Initializing...")
        self.assertEqual(status["to_work"]["time_mins"], 0)

    def test_read_from_file(self):
        """Test that status reads from the JSON file."""
        test_data = self.store.default_state.copy()
        test_data["last_updated"] = "12:00:00"
        test_data["to_work"]["time_mins"] = 30
        
        with open(DATA_FILE, 'w') as f:
            json.dump(test_data, f)
            
        status = self.store.status
        self.assertEqual(status["last_updated"], "12:00:00")
        self.assertEqual(status["to_work"]["time_mins"], 30)

    def test_persistence_logic(self):
        """
        We cannot easily test `update()` without mocking all external APIs.
        But we can test the file writing logic if we extract it or mock the calls.
        For now, let's verify that if we *manually* write to the file (simulating update),
        it works.
        """
        # Simulate update process writing a file
        new_state = {
            "to_work": {"time_mins": 45, "distance_km": 50, "trend": "up", "color": "heavy-traffic"},
            "to_home": {"time_mins": 40, "distance_km": 50, "trend": "flat", "color": ""},
            "weather": {"temp": 20, "feels_like": 18, "description": "Sunny", "emoji": "☀️"},
            "traffic_alerts": ["Accident on E19"],
            "spotify": {"is_playing": True, "title": "Test Song", "artist": "Test Artist", "cover_url": "http://img"},
            "last_updated": "12:34:56"
        }
        
        with open(DATA_FILE, 'w') as f:
            json.dump(new_state, f)
            
        # Check if store picks it up
        status = self.store.status
        self.assertEqual(status["weather"]["temp"], 20)
        self.assertEqual(status["spotify"]["title"], "Test Song")

if __name__ == '__main__':
    unittest.main()
