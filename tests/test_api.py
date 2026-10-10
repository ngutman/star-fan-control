import unittest
from unittest.mock import patch
from app import app
from radio import RadioBusy, RadioError


class APITests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.mock = patch('control_fan.send').start()
        self.addCleanup(patch.stopall)

    def test_existing_fans(self):
        for address in (28, 10):
            response = self.client.get(f'/control/{address}/speed3')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'<p>Done!</p>')
        self.assertEqual(self.mock.call_count, 2)

    def test_new_fan(self):
        for command in ('on', 'off', 'speed1', 'speed6'):
            response = self.client.get(f'/control/fc980rs/fbf905/{command}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'transmitted')

    def test_invalid_requests_do_not_transmit(self):
        for path in ('/control/no/speed1', '/control/32/power', '/control/10/no',
                     '/control/fc980rs/31/on', '/control/fc980rs/fbf905/reverse'):
            self.assertEqual(self.client.get(path).status_code, 400)
        self.mock.assert_not_called()

    def test_liveness_does_not_transmit(self):
        self.assertEqual(self.client.get('/health').json, {'status': 'ok'})
        self.mock.assert_not_called()

    def test_radio_errors_are_not_success(self):
        for error in (RadioBusy('busy'), RadioError('failed')):
            self.mock.side_effect = error
            response = self.client.get('/control/fc980rs/fbf905/speed1')
            self.assertEqual(response.status_code, 503)
            if isinstance(error, RadioBusy):
                self.assertEqual(response.headers['Retry-After'], '2')
