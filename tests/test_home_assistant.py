import concurrent.futures
import unittest
from unittest.mock import Mock

import requests
from flask import Flask

from modules.floorplan_config import SENSORS
from modules.home_assistant import HomeAssistantClient, create_floorplan_blueprint


class HomeAssistantTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.response = self.session.get.return_value
        self.response.status_code = 200
        self.response.json.return_value = [
            {'entity_id': s.entity_id, 'state': 'off', 'last_changed': '2026-09-11T12:00:00+00:00'}
            for s in SENSORS
        ]
        self.now = 100
        self.client = HomeAssistantClient('http://ha.test:8123', 'test-secret', session=self.session, clock=lambda: self.now)
        app = Flask(__name__, template_folder='../templates', static_folder='../static')
        app.register_blueprint(create_floorplan_blueprint(self.client))
        self.http = app.test_client()

    def test_states_are_allowlisted_and_normalized(self):
        self.response.json.return_value[0]['state'] = 'on'
        self.response.json.return_value[1]['state'] = 'unknown'
        self.response.json.return_value[2]['state'] = 'unavailable'
        self.response.json.return_value[3]['state'] = 'unexpected'
        self.response.json.return_value.pop()
        self.response.json.return_value.append({'entity_id': 'sensor.private', 'state': 'secret'})
        result = self.client.snapshot()
        self.assertEqual(result['counts'], {'open': 1, 'closed': 12, 'unavailable': 4})
        self.assertEqual(result['sensors'][0]['state'], 'open')
        self.assertNotIn('sensor.private', str(result))
        self.assertNotIn('test-secret', str(result))
        self.assertIsNotNone(result['last_success'])

    def test_shared_cache_and_recovery(self):
        first = self.client.snapshot()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda _: self.client.snapshot(), range(10)))
        self.assertEqual(results, [first] * 10)
        self.session.get.assert_called_once()
        self.now += 4
        self.session.get.side_effect = requests.Timeout('test-secret')
        failed = self.client.snapshot()
        self.assertEqual(failed['counts']['unavailable'], 17)
        self.assertEqual(failed['counts']['closed'], 0)
        self.assertEqual(failed['last_success'], first['last_success'])
        self.assertNotIn('test-secret', str(failed))
        self.client.snapshot()
        self.assertEqual(self.session.get.call_count, 2)
        self.now += 4
        self.session.get.side_effect = None
        self.assertEqual(self.client.snapshot()['counts']['closed'], 17)

    def test_concurrent_initial_refresh_is_coalesced(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(lambda _: self.client.snapshot(), range(10)))
        self.session.get.assert_called_once()

    def test_missing_token_makes_no_request(self):
        self.client.access_token = ''
        self.assertEqual(self.client.snapshot()['status'], 'not_configured')
        self.session.get.assert_not_called()

    def test_bad_url_makes_no_request(self):
        for url in ('file:///etc/passwd', 'http://name:secret@ha.test', 'http://ha.test?token=secret'):
            with self.subTest(url=url):
                client = HomeAssistantClient(url, 'test-secret', session=self.session)
                self.assertEqual(client.snapshot()['status'], 'configuration_error')
        self.session.get.assert_not_called()

    def test_authentication_and_server_errors_are_sanitized(self):
        for code, status in ((401, 'authentication_error'), (403, 'authentication_error'), (500, 'offline'), (302, 'offline')):
            with self.subTest(code=code):
                self.response.status_code = code
                self.now += 4
                result = self.client.snapshot()
                self.assertEqual(result['status'], status)
                self.assertEqual(result['counts']['unavailable'], 17)
                self.assertNotIn('test-secret', str(result))

    def test_malformed_json_and_shape_fail_safely(self):
        self.response.json.side_effect = ValueError('test-secret')
        self.assertEqual(self.client.snapshot()['status'], 'offline')
        self.response.json.side_effect = None
        for data in ({}, None, [None]):
            self.now += 4
            self.response.json.return_value = data
            self.assertEqual(self.client.snapshot()['status'], 'offline')

    def test_all_entities_missing_does_not_look_closed(self):
        self.response.json.return_value = []
        result = self.client.snapshot()
        self.assertEqual(result['status'], 'connected')
        self.assertEqual(result['counts']['unavailable'], 17)

    def test_api_contract_and_request_security(self):
        response = self.http.get('/api/ha/floorplan')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertEqual(len(response.json['sensors']), 17)
        args, kwargs = self.session.get.call_args
        self.assertEqual(args[0], 'http://ha.test:8123/api/states')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-secret')
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(kwargs['timeout'], (2, 3))
        self.assertNotIn('test-secret', response.get_data(as_text=True))
        self.assertEqual(self.http.post('/api/ha/floorplan').status_code, 405)

    def test_api_failure_is_503_and_never_returns_old_closed_states(self):
        self.http.get('/api/ha/floorplan')
        self.now += 4
        self.session.get.side_effect = requests.ConnectionError('test-secret')
        response = self.http.get('/api/ha/floorplan')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json['counts']['unavailable'], 17)

    def test_page_never_contacts_ha_or_exposes_token(self):
        response = self.http.get('/floorplan')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(html.count('class="fp-sensor"'), 17)
        self.assertIn('data-view="floorplan" aria-current="page"', html)
        self.assertNotIn('test-secret', html)
        self.session.get.assert_not_called()

    def test_callers_cannot_mutate_cache(self):
        self.client.snapshot()['sensors'][0]['state'] = 'open'
        self.assertEqual(self.client.snapshot()['sensors'][0]['state'], 'closed')


if __name__ == '__main__':
    unittest.main()
