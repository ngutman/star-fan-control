"""Original five-bit address / eight-bit command protocol."""
from protocols import Transmission

BUTTONS = {
    'power': 0x84, 'light': 0x82,
    'speed1': 0x90, 'speed2': 0x94, 'speed3': 0xA0,
    'speed4': 0xB0, 'speed5': 0xC4, 'speed6': 0xC0,
}


def encode_command(raw_command: int) -> bytes:
    encoded = 0
    for i in reversed(range(13)):
        encoded = (encoded << 3) | (0b101 if raw_command & (1 << i) else 0b100)
    return encoded.to_bytes(5, 'big')


def build(fan_id: int, command: str) -> Transmission:
    if not 0 <= fan_id <= 31:
        raise ValueError('Star 7 fan ID must be between 0 and 31')
    if command not in BUTTONS:
        raise ValueError('Unsupported Star 7 command')
    packet = encode_command((fan_id << 8) | BUTTONS[command])
    return Transmission((packet,) * 10, minimum_interval=0.015)
