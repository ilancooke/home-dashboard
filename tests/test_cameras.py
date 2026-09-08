import unittest

from flask import Flask

from modules.cameras import (
    Camera,
    FrigateUnavailableError,
    create_camera_blueprint,
)


class FakeFrigateClient:
    def __init__(self):
        self.calls = []
        self.unavailable = False

    def latest_frame(self, camera):
        self.calls.append(camera)
        if self.unavailable:
            raise FrigateUnavailableError("Frigate camera image is unavailable")
        return b"camera-image", "image/jpeg"


class CameraRouteTests(unittest.TestCase):
    def setUp(self):
        self.frigate = FakeFrigateClient()
        app = Flask(__name__, template_folder="../templates")
        app.register_blueprint(create_camera_blueprint(self.frigate))
        app.testing = True
        self.client = app.test_client()

    def test_camera_page_shows_the_configured_camera_grid(self):
        response = self.client.get("/cameras")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-view="cameras" aria-current="page"', html)
        self.assertIn("Back Patio", html)
        self.assertIn("West Gate", html)
        self.assertEqual(self.frigate.calls, [])

    def test_camera_api_lists_all_five_cameras(self):
        response = self.client.get("/api/cameras")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [
            {"id": "back_patio", "name": "Back Patio"},
            {"id": "driveway", "name": "Driveway"},
            {"id": "east_gate", "name": "East Gate"},
            {"id": "front_yard", "name": "Front Yard"},
            {"id": "west_gate", "name": "West Gate"},
        ])

    def test_camera_image_is_proxied_without_caching(self):
        response = self.client.get("/api/cameras/front_yard/latest.jpg")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"camera-image")
        self.assertEqual(response.content_type, "image/jpeg")
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        self.assertEqual(self.frigate.calls, [Camera("front_yard", "Front Yard")])

    def test_unknown_camera_and_frigate_errors_are_safe(self):
        unknown_response = self.client.get("/api/cameras/unknown/latest.jpg")
        self.frigate.unavailable = True
        unavailable_response = self.client.get("/api/cameras/driveway/latest.jpg")

        self.assertEqual(unknown_response.status_code, 404)
        self.assertEqual(unavailable_response.status_code, 503)
        self.assertEqual(self.frigate.calls, [Camera("driveway", "Driveway")])


if __name__ == "__main__":
    unittest.main()
