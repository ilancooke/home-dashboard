"""Flask page and JSON API for whole-home audio controls."""

from flask import Blueprint, jsonify, render_template, request

from .config import SOURCE_NAMES, ZONE_NAMES
from .controller import (
    AudioResponseError,
    AudioTimeoutError,
    AudioUnavailableError,
)
from .protocol import ProtocolError


class RequestValidationError(ValueError):
    pass


def _validate_zone(zone):
    if zone not in ZONE_NAMES:
        raise RequestValidationError("zone must be between 1 and 6")
    return zone


def _json_value(name, expected_type, minimum=None, maximum=None):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {name}:
        raise RequestValidationError(f"JSON body must contain only '{name}'")

    value = body[name]
    if expected_type is bool:
        if not isinstance(value, bool):
            raise RequestValidationError(f"'{name}' must be a boolean")
    elif isinstance(value, bool) or not isinstance(value, expected_type):
        raise RequestValidationError(f"'{name}' must be an integer")

    if minimum is not None and not minimum <= value <= maximum:
        raise RequestValidationError(
            f"'{name}' must be between {minimum} and {maximum}"
        )
    return value


def _display_status(status):
    result = dict(status)
    zone = result["zone"]
    source = result["source"]
    result["name"] = ZONE_NAMES[zone]
    result["source_name"] = SOURCE_NAMES.get(source, f"Input {source}")
    return result


def create_audio_blueprint(controller):
    blueprint = Blueprint("audio", __name__)

    @blueprint.get("/audio")
    def audio_page():
        return render_template(
            "audio.html",
            zone_names=ZONE_NAMES,
            source_names=SOURCE_NAMES,
        )

    @blueprint.get("/api/audio/zones")
    def all_zones():
        return jsonify([
            _display_status(status)
            for status in controller.get_all_zone_statuses()
        ])

    @blueprint.get("/api/audio/zones/<int:zone>")
    def zone_status(zone):
        _validate_zone(zone)
        return jsonify(_display_status(controller.get_zone_status(zone)))

    @blueprint.post("/api/audio/zones/<int:zone>/power")
    def set_power(zone):
        _validate_zone(zone)
        on = _json_value("on", bool)
        return jsonify(_display_status(controller.set_power(zone, on)))

    @blueprint.post("/api/audio/zones/<int:zone>/source")
    def set_source(zone):
        _validate_zone(zone)
        source = _json_value("source", int, 1, 6)
        return jsonify(_display_status(controller.set_source(zone, source)))

    @blueprint.post("/api/audio/zones/<int:zone>/volume")
    def set_volume(zone):
        _validate_zone(zone)
        volume = _json_value("volume", int, 0, 38)
        return jsonify(_display_status(controller.set_volume(zone, volume)))

    @blueprint.post("/api/audio/zones/<int:zone>/mute")
    def set_mute(zone):
        _validate_zone(zone)
        muted = _json_value("muted", bool)
        return jsonify(_display_status(controller.set_mute(zone, muted)))

    @blueprint.errorhandler(RequestValidationError)
    @blueprint.errorhandler(ProtocolError)
    def invalid_request(error):
        return jsonify(error=str(error)), 400

    @blueprint.errorhandler(AudioUnavailableError)
    def audio_unavailable(error):
        return jsonify(error=str(error)), 503

    @blueprint.errorhandler(AudioTimeoutError)
    def audio_timeout(error):
        return jsonify(error=str(error)), 504

    @blueprint.errorhandler(AudioResponseError)
    def invalid_response(error):
        return jsonify(error=str(error)), 502

    return blueprint
