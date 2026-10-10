import unittest
import json
from pathlib import Path
from protocols import fc980rs, star7


class ProtocolTests(unittest.TestCase):
    def test_legacy_matches_original_for_every_address_and_command(self):
        for address in range(32):
            for command, code in star7.BUTTONS.items():
                raw = (address << 8) | code
                expected = int(''.join('101' if raw & (1 << i) else '100'
                                       for i in reversed(range(13))), 2).to_bytes(5, 'big')
                burst = star7.build(address, command)
                self.assertEqual(burst.packets, (expected,) * 10)
                self.assertEqual(burst.minimum_interval, .015)

    def test_invalid_legacy_input(self):
        for address, command in [(-1, 'power'), (32, 'power'), (28, 'off'), (10, 'invalid')]:
            with self.assertRaises(ValueError):
                star7.build(address, command)

    def test_captured_waveform_and_pair_padding(self):
        # Literal 161-symbol frame from power-capture.jsonl, repeated identically.
        captured = ('111011101110111011101000111011101110111011101110111010001000111010001000'
                    '100010001000111010001110100010001000100010001110111011101000100010001000'
                    '10001110111011101')
        self.assertEqual(len(captured), 161)
        self.assertEqual(fc980rs.frame(bytes.fromhex('fbf905'), 7), captured + '0' * 16)
        packet = fc980rs.build('fbf905', 'on').packets[0]
        self.assertEqual(f'{int.from_bytes(packet, "big"):0360b}',
                         (captured + '0' * 16) * 2 + '0' * 6)

    def test_speed_command_frames_and_burst_order(self):
        for name, code in [('on', 7), ('off', 8), ('light_toggle', 11)] + [(f'speed{i}', i) for i in range(1, 7)]:
            burst = fc980rs.build('FBF905', name)
            self.assertEqual(len(burst.packets), 4)
            for packet, phase in zip(burst.packets, [code, code, code | 64, code | 64]):
                self.assertEqual(len(packet), 45)
                bits = f'{int.from_bytes(packet, "big"):0360b}'
                for offset in (0, 177):
                    symbols = [bits[offset+i:offset+i+4] for i in range(0, 160, 4)]
                    self.assertTrue(all(s in ('1000', '1110') for s in symbols))
                    decoded = int(''.join('1' if s == '1110' else '0' for s in symbols), 2)
                    self.assertEqual(decoded.to_bytes(5, 'big'), bytes.fromhex('fbf905') + bytes([phase, phase]))
                    self.assertEqual(bits[offset+160:offset+177], '1' + '0' * 16)

    def test_invalid_new_input(self):
        for prefix, command in [('31', 'on'), ('fbf90z', 'on'), ('1234567', 'on'),
                                ('fbf905', 'power'), ('fbf905', 'speed0'), ('fbf905', 'light')]:
            with self.assertRaises(ValueError):
                fc980rs.build(prefix, command)

    def test_light_toggle_matches_both_physical_transitions(self):
        fixtures = json.loads(Path('tests/fixtures/fc980rs-light.json').read_text())
        self.assertEqual({f['transition'] for f in fixtures}, {'off_to_on', 'on_to_off'})
        burst = fc980rs.build('fbf905', 'light_toggle')
        for capture in fixtures:
            payload = bytes.fromhex(capture['payload'])
            self.assertIn(payload[-1], (0x0B, 0x4B))
            packet = burst.packets[0 if payload[-1] == 0x0B else 2]
            self.assertEqual(f'{int.from_bytes(packet, "big"):0360b}'[:161], capture['symbols'])
