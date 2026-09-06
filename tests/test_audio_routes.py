import unittest

from flask import Flask

from modules.audio.routes import create_audio_blueprint


class FakeController:
    def __init__(self):
        self.calls = []

    @staticmethod
    def _status(zone):
        return {
            "zone": zone,
            "power": False,
            "mute": False,
            "volume": 15,
            "treble": 7,
            "bass": 7,
            "balance": 10,
            "source": 1,
            "pa": False,
            "do_not_disturb": False,
            "keypad_connected": True,
        }

    def get_all_zone_statuses(self):
        return [self._status(zone) for zone in range(1, 7)]

    def get_zone_status(self, zone):
        return self._status(zone)

    def set_power(self, zone, value):
        self.calls.append(("power", zone, value))
        status = self._status(zone)
        status["power"] = value
        return status

    def set_source(self, zone, value):
        self.calls.append(("source", zone, value))
        status = self._status(zone)
        status["source"] = value
        return status

    def set_volume(self, zone, value):
        self.calls.append(("volume", zone, value))
        status = self._status(zone)
        status["volume"] = value
        return status

    def set_mute(self, zone, value):
        self.calls.append(("mute", zone, value))
        status = self._status(zone)
        status["mute"] = value
        return status


class AudioRouteTests(unittest.TestCase):
    def setUp(self):
        self.controller = FakeController()
        app = Flask(__name__, template_folder="../templates")
        app.register_blueprint(create_audio_blueprint(self.controller))
        app.testing = True
        self.client = app.test_client()

    def test_lists_all_six_named_zones(self):
        response = self.client.get("/api/audio/zones")

        self.assertEqual(response.status_code, 200)
        zones = response.get_json()
        self.assertEqual(len(zones), 6)
        self.assertEqual(zones[0]["name"], "Lounge")
        self.assertEqual(zones[0]["source_name"], "Echo Dot")

    def test_unused_zones_remain_available_through_the_api(self):
        response = self.client.get("/api/audio/zones/5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["name"], "Zone 5")

    def test_updates_a_valid_zone(self):
        response = self.client.post(
            "/api/audio/zones/2/volume",
            json={"volume": 23},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["volume"], 23)
        self.assertEqual(self.controller.calls, [("volume", 2, 23)])

    def test_rejects_invalid_values_without_calling_controller(self):
        responses = (
            self.client.post("/api/audio/zones/1/power", json={"on": 1}),
            self.client.post("/api/audio/zones/1/source", json={"source": 7}),
            self.client.post("/api/audio/zones/1/volume", json={"volume": -1}),
            self.client.post("/api/audio/zones/7/mute", json={"muted": True}),
        )

        self.assertTrue(all(response.status_code == 400 for response in responses))
        self.assertEqual(self.controller.calls, [])


if __name__ == "__main__":
    unittest.main()
