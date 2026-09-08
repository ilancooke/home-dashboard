"""Frigate camera snapshots for the home dashboard."""

from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests
from flask import Blueprint, Response, jsonify, render_template


@dataclass(frozen=True)
class Camera:
    identifier: str
    name: str


CAMERAS = (
    Camera("back_patio", "Back Patio"),
    Camera("driveway", "Driveway"),
    Camera("east_gate", "East Gate"),
    Camera("front_yard", "Front Yard"),
    Camera("west_gate", "West Gate"),
)
CAMERAS_BY_IDENTIFIER = {camera.identifier: camera for camera in CAMERAS}


class FrigateUnavailableError(RuntimeError):
    """Frigate could not provide a requested camera image."""


class FrigateClient:
    def __init__(self, base_url, live_url=None, access_token=None, session=requests):
        self.base_url = base_url.rstrip("/")
        self.live_url = (live_url or base_url).rstrip("/")
        self.access_token = access_token
        self.session = session

    def latest_frame(self, camera):
        headers = {"Accept": "image/jpeg"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            response = self.session.get(
                f"{self.base_url}/api/{camera.identifier}/latest.jpg",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise FrigateUnavailableError("Frigate camera image is unavailable") from error

        content_type = response.headers.get("Content-Type", "image/jpeg")
        if not content_type.startswith("image/"):
            raise FrigateUnavailableError("Frigate returned an invalid camera image")

        return response.content, content_type

    def mse_websocket_url(self, camera):
        parts = urlsplit(self.live_url)
        scheme = {"http": "ws", "https": "wss"}.get(parts.scheme)
        if scheme is None or not parts.netloc:
            raise FrigateUnavailableError("Frigate live URL is invalid")
        return urlunsplit((
            scheme,
            parts.netloc,
            "/live/mse/api/ws",
            urlencode({"src": camera.identifier}),
            "",
        ))


def create_camera_blueprint(client):
    blueprint = Blueprint("cameras", __name__)

    @blueprint.get("/cameras")
    def cameras_page():
        return render_template("cameras.html", cameras=CAMERAS)

    @blueprint.get("/api/cameras")
    def cameras():
        return jsonify([
            {"id": camera.identifier, "name": camera.name}
            for camera in CAMERAS
        ])

    @blueprint.get("/api/cameras/<camera_id>/latest.jpg")
    def latest_frame(camera_id):
        camera = CAMERAS_BY_IDENTIFIER.get(camera_id)
        if camera is None:
            return jsonify(error="Unknown camera"), 404

        image, content_type = client.latest_frame(camera)
        return Response(
            image,
            content_type=content_type,
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    @blueprint.get("/api/cameras/<camera_id>/live")
    def live_stream(camera_id):
        camera = CAMERAS_BY_IDENTIFIER.get(camera_id)
        if camera is None:
            return jsonify(error="Unknown camera"), 404
        return jsonify(url=client.mse_websocket_url(camera))

    @blueprint.errorhandler(FrigateUnavailableError)
    def frigate_unavailable(error):
        return jsonify(error=str(error)), 503

    return blueprint
