import unittest
from unittest.mock import patch
from app import create_app

class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_morning_display(self):
        # We need to patch where it is USED.
        # In app/routes.py: from . import routes (in create_app)
        # routes.py defines dashboard which calls get_commute_mode.
        # So we patch app.routes.get_commute_mode
        with patch('app.routes.get_commute_mode', return_value='to_work'):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            # Check for text "Home ➝ Work"
            text = response.data.decode('utf-8')
            self.assertIn('Home ➝ Work', text)
            self.assertNotIn('Work ➝ Home', text)

    def test_afternoon_display(self):
        with patch('app.routes.get_commute_mode', return_value='to_home'):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            text = response.data.decode('utf-8')
            self.assertIn('Work ➝ Home', text)
            self.assertNotIn('Home ➝ Work', text)

if __name__ == '__main__':
    unittest.main()
