"""Protocol dispatch, preserving the existing Python entry point."""
from protocols import fc980rs, star7
from protocols.star7 import BUTTONS, encode_command  # compatibility imports
from radio import send


def control_fan(fan_id: int, command: str):
    send(star7.build(fan_id, command))


def control_fc980rs(prefix: str, command: str):
    send(fc980rs.build(prefix, command))
