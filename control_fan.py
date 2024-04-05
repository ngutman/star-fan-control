import cc1101
import logging
from time import sleep

TXGPIO = 26
SYMBOL_BAUD = 3300
REPEAT_COUNT = 10

BUTTONS = {
    'power': 0x84,
    'light': 0x82,
    'speed1': 0x90,
    'speed2': 0x94,
    'speed3': 0xa0,
    'speed4': 0xb0,
    'speed5': 0xc4,
    'speed6': 0xc0,
}

logger = logging.getLogger('control_fan')

def encode_command(raw_command: int) -> bytes:
    encoded_command = 0
    for i in reversed(range(13)):
        if (raw_command & (1 << i)):
            encoded_command = (encoded_command << 3) | 0b101
        else:
            encoded_command = (encoded_command << 3) | 0b100
    return encoded_command.to_bytes(5)

def send_command(command: bytes):
    with cc1101.CC1101() as transceiver:
        transceiver.set_base_frequency_hertz(433.92e6)
        transceiver.set_sync_mode(cc1101.SyncMode.NO_PREAMBLE_AND_SYNC_WORD)
        transceiver.set_packet_length_mode(cc1101.PacketLengthMode.FIXED)
        transceiver.set_packet_length_bytes(5)
        transceiver.disable_checksum()
        transceiver.set_symbol_rate_baud(SYMBOL_BAUD)
        transceiver.set_output_power((0, 0xC0))

        for x in range(REPEAT_COUNT):
            transceiver.transmit(command)
            sleep(0.015)

def control_fan(fan_id: int, command: str):    
    command_id = BUTTONS.get(command)
    if not command_id:
        logger.error(f'Can\'t find command "{command}"')
        return
    logger.info(f'Executing command {command} on fan id {fan_id}')
    fan_id = fan_id & 0b11111
    raw_command = (fan_id << 8) | command_id

    encoded_command = encode_command(raw_command)
    logger.debug(f'Encoded command = {encoded_command.hex()}')
    
    send_command(encoded_command)
