import unittest
from unittest.mock import patch

from app import app


class DashboardPageTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("app.get_weather")
    def test_weather_renders_in_shared_dashboard(self, get_weather):
        get_weather.return_value = ([], [{
            "temperature": 99,
            "temperatureUnit": "F",
            "shortForecast": "Sunny",
            "displayTime": "3 PM",
            "symbol": "☀",
            "windSpeed": "5 mph",
            "probabilityOfPrecipitation": {"value": 0},
        }], None)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("99°F", html)
        self.assertIn('data-view="weather" aria-current="page"', html)
        self.assertIn('id="fullscreen-button"', html)
        self.assertNotIn('http-equiv="refresh"', html)

    @patch("app.get_weather", return_value=([], [], "Weather unavailable"))
    def test_weather_failure_keeps_audio_navigation_available(self, get_weather):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Weather data temporarily unavailable.", html)
        self.assertIn('href="/audio"', html)
        self.assertIn('href="/cameras"', html)

    @patch("app.audio_controller.get_all_zone_statuses")
    def test_direct_audio_page_has_shared_navigation_without_serial_access(self, get_zones):
        response = self.client.get("/audio")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-view="audio" aria-current="page"', html)
        self.assertIn('id="fullscreen-button"', html)
        self.assertIn("Master Bathroom", html)
        self.assertNotIn('id="zone-5"', html)
        get_zones.assert_not_called()


if __name__ == "__main__":
    unittest.main()
