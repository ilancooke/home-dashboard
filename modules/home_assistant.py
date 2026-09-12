"""Read-only Home Assistant state access, shared cached polling, and floorplan routes."""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit

import requests
from flask import Blueprint, jsonify, render_template

from modules.floorplan_config import SENSORS


class HomeAssistantClient:
    CACHE_SECONDS = 3

    def __init__(self, base_url, access_token=None, session=None, clock=monotonic):
        self.base_url = (base_url or '').strip().rstrip('/')
        self.access_token = (access_token or '').strip()
        self.session = session if session is not None else requests.Session()
        self.clock = clock
        self.lock = Lock()
        self.cached = None
        self.expires_at = 0
        self.last_success = None

    def _result(self, status, message, states=None):
        states = states or {}
        sensors = []
        for sensor in SENSORS:
            entity = states.get(sensor.entity_id, {})
            raw = entity.get('state')
            state = ('open' if raw == sensor.open_state else
                     'closed' if raw == sensor.closed_state else 'unavailable')
            changed = entity.get('last_changed')
            sensors.append({
                'id': sensor.id,
                'state': state,
                'last_changed': changed if isinstance(changed, str) else None,
            })
        return {
            'status': status, 'message': message,
            'last_success': self.last_success,
            'sensors': sensors,
            'counts': {state: sum(s['state'] == state for s in sensors)
                       for state in ('open', 'closed', 'unavailable')},
        }

    def _fetch(self):
        if not self.access_token:
            return self._result('not_configured', 'Home Assistant not configured.')
        try:
            parts = urlsplit(self.base_url)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
                return self._result('configuration_error', 'Home Assistant address is invalid.')
            response = self.session.get(
                self.base_url + '/api/states',
                headers={'Authorization': 'Bearer ' + self.access_token, 'Accept': 'application/json'},
                timeout=(2, 3), allow_redirects=False,
            )
            if response.status_code in (401, 403):
                return self._result('authentication_error', 'Home Assistant authentication failed.')
            if response.status_code != 200:
                return self._result('offline', 'Home Assistant is unavailable. Retrying automatically.')
            data = response.json()
            if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
                return self._result('offline', 'Home Assistant returned invalid sensor data.')
            allowed = {sensor.entity_id for sensor in SENSORS}
            states = {row['entity_id']: row for row in data
                      if isinstance(row.get('entity_id'), str) and row['entity_id'] in allowed}
            self.last_success = datetime.now(timezone.utc).isoformat()
            return self._result('connected', 'Connected to Home Assistant.', states)
        except (requests.RequestException, ValueError):
            # Never return upstream response bodies, exception text, or credentials.
            return self._result('offline', 'Home Assistant is unavailable. Retrying automatically.')

    def snapshot(self):
        # Serialize refreshes so concurrent tablets share one request and session.
        # Cache failures too, avoiding a request storm while HA is down.
        with self.lock:
            if self.cached is None or self.clock() >= self.expires_at:
                self.cached = self._fetch()
                self.expires_at = self.clock() + self.CACHE_SECONDS
            return deepcopy(self.cached)


def create_floorplan_blueprint(client):
    blueprint = Blueprint('floorplan', __name__)

    @blueprint.get('/floorplan')
    def floorplan():
        return render_template('floorplan.html', sensors=SENSORS)

    @blueprint.get('/api/ha/floorplan')
    def states():
        snapshot = client.snapshot()
        response = jsonify(snapshot)
        response.status_code = 200 if snapshot['status'] == 'connected' else 503
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        return response

    return blueprint
