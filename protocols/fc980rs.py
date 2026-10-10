"""FC980RS-DPS captured protocol variant; see docs/protocol-fc980rs.md."""
import re
from protocols import Transmission

COMMANDS = {f'speed{i}': i for i in range(1, 7)} | {'on': 7, 'off': 8, 'light_toggle': 11}


def frame(prefix: bytes, command: int) -> str:
    # The repeated byte is observed, not a claimed general checksum algorithm.
    data = prefix + bytes([command, command])
    return ''.join('1110' if bit == '1' else '1000'
                   for byte in data for bit in f'{byte:08b}') + '1' + '0' * 16


def build(prefix: str, command: str) -> Transmission:
    if not re.fullmatch(r'[0-9a-fA-F]{6}', prefix):
        raise ValueError('FC980RS prefix must contain exactly six hexadecimal digits')
    if command not in COMMANDS:
        raise ValueError('Unsupported FC980RS command; use on, off, light_toggle, or speed1 through speed6')
    address = bytes.fromhex(prefix)
    packets = []
    code = COMMANDS[command]
    for phase in (code, code | 0x40):
        # Two frames fit inside the 64-byte FIFO. Pad only the final low gap.
        bits = frame(address, phase) * 2
        bits += '0' * (-len(bits) % 8)
        packet = int(bits, 2).to_bytes(len(bits) // 8, 'big')
        packets.extend((packet, packet))
    return Transmission(tuple(packets))
