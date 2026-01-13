import unittest
from datetime import datetime
from app import create_app

class TestCommuteLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        # Now we can import routes
        # Note: We need to import inside here because app.routes expects an active app context
        # when it is imported (due to @app.route decorator on current_app proxy)
        from app.routes import get_commute_mode
        cls.get_commute_mode = staticmethod(get_commute_mode)

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_morning_commute(self):
        get_commute_mode = self.get_commute_mode
        # 00:00 -> to_work
        t = datetime(2023, 1, 1, 0, 0, 0)
        self.assertEqual(get_commute_mode(t), "to_work", "00:00 should be to_work")

        # 09:59 -> to_work
        t = datetime(2023, 1, 1, 9, 59, 59)
        self.assertEqual(get_commute_mode(t), "to_work", "09:59:59 should be to_work")

        # 10:00:00 -> to_work
        t = datetime(2023, 1, 1, 10, 0, 0)
        self.assertEqual(get_commute_mode(t), "to_work", "10:00:00 should be to_work")

        # 10:00:59 -> to_work
        t = datetime(2023, 1, 1, 10, 0, 59)
        self.assertEqual(get_commute_mode(t), "to_work", "10:00:59 should be to_work")

    def test_afternoon_commute(self):
        get_commute_mode = self.get_commute_mode
        # 10:01:00 -> to_home
        t = datetime(2023, 1, 1, 10, 1, 0)
        self.assertEqual(get_commute_mode(t), "to_home", "10:01:00 should be to_home")

        # 12:00 -> to_home
        t = datetime(2023, 1, 1, 12, 0, 0)
        self.assertEqual(get_commute_mode(t), "to_home", "12:00:00 should be to_home")

        # 23:59 -> to_home
        t = datetime(2023, 1, 1, 23, 59, 59)
        self.assertEqual(get_commute_mode(t), "to_home", "23:59:59 should be to_home")

if __name__ == '__main__':
    unittest.main()
