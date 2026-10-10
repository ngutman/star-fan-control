import multiprocessing
import os
import tempfile
import types
import unittest
from unittest.mock import patch
from protocols import Transmission
from radio import RadioBusy, RadioError, radio_lock, send


def contend(path, result):
    try:
        with radio_lock(path, timeout=.05):
            result.put('acquired')
    except RadioBusy:
        result.put('busy')


class RadioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = os.path.join(self.temp.name, 'radio.lock')
        self.states = [20, 19, 1]  # transient TX states omitted by upstream enum
        self.sent = []
        self.strobes = []
        self.settings = []
        outer = self
        class Fake:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __getattr__(self, name):
                return lambda *args: outer.settings.append((name, args))
            def transmit(self, data): outer.sent.append(data)
            def _read_status_register(self, _):
                return outer.states.pop(0) if len(outer.states) > 1 else outer.states[0]
            def _command_strobe(self, value): outer.strobes.append(value)
        module = types.ModuleType('cc1101')
        module.CC1101 = Fake
        module.SyncMode = types.SimpleNamespace(NO_PREAMBLE_AND_SYNC_WORD=0)
        module.PacketLengthMode = types.SimpleNamespace(FIXED=0)
        addresses = types.ModuleType('cc1101.addresses')
        addresses.StrobeAddress = types.SimpleNamespace(SIDLE=0x36)
        addresses.StatusRegisterAddress = types.SimpleNamespace(MARCSTATE=0x35)
        patch.dict('sys.modules', {'cc1101': module, 'cc1101.addresses': addresses}).start()
        patch.dict(os.environ, {'FAN_RADIO_LOCK': self.path}).start()
        self.addCleanup(patch.stopall)

    def test_transient_states_and_complete_burst(self):
        send(Transmission((b'one', b'two')))
        self.assertEqual(self.sent, [b'one', b'two'])
        self.assertEqual(self.strobes, [0x36])
        self.assertIn(('set_base_frequency_hertz', (433.92e6,)), self.settings)

    def test_underflow_restores_idle_and_releases_lock(self):
        self.states = [22]
        with self.assertRaisesRegex(RadioError, 'underflow'):
            send(Transmission((b'one', b'two')))
        self.assertEqual(self.sent, [b'one'])
        self.assertEqual(self.strobes, [0x36])
        with radio_lock(self.path, timeout=0): pass

    def test_timeout_is_bounded(self):
        self.states = [19]
        with patch('radio.time.monotonic', side_effect=[0, 0, 2]):
            with self.assertRaisesRegex(RadioError, 'timed out'):
                send(Transmission((b'one',)))
        self.assertEqual(self.strobes, [0x36])

    def test_fifo_limits(self):
        for packets in ((), (b'',), (b'a' * 65,)):
            with self.assertRaises(ValueError): send(Transmission(packets))
        self.assertEqual(self.sent, [])

    def test_process_lock_contention_and_release(self):
        ctx = multiprocessing.get_context('spawn')
        result = ctx.Queue()
        with radio_lock(self.path):
            child = ctx.Process(target=contend, args=(self.path, result))
            child.start(); child.join(5)
            self.assertFalse(child.is_alive())
            self.assertEqual(result.get(timeout=1), 'busy')
        child = ctx.Process(target=contend, args=(self.path, result))
        child.start(); child.join(5)
        self.assertEqual(result.get(timeout=1), 'acquired')
        result.close()
