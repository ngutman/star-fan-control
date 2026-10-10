"""Serialize complete bursts across Gunicorn workers and bound hardware waits."""
from contextlib import contextmanager
import fcntl
import logging
import os
import time

from protocols import Transmission

logger = logging.getLogger(__name__)


class RadioBusy(RuntimeError):
    pass


class RadioError(RuntimeError):
    pass


@contextmanager
def radio_lock(path=None, timeout=2.0):
    path = path or os.environ.get('FAN_RADIO_LOCK', '/tmp/star-fan-control.lock')
    with open(path, 'a') as lock:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RadioBusy('Radio is busy; retry after the current command')
                time.sleep(0.01)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def send(transmission: Transmission):
    # Import lazily so encoders/API can be tested without Raspberry Pi hardware.
    import cc1101
    from cc1101.addresses import StrobeAddress as Strobe, StatusRegisterAddress as Status

    if not transmission.packets or any(not 1 <= len(p) <= 64 for p in transmission.packets):
        raise ValueError('Packets must fit the 64-byte CC1101 FIFO')
    with radio_lock():
        try:
            with cc1101.CC1101() as device:
                try:
                    device.set_base_frequency_hertz(433.92e6)
                    device.set_sync_mode(cc1101.SyncMode.NO_PREAMBLE_AND_SYNC_WORD)
                    device.set_packet_length_mode(cc1101.PacketLengthMode.FIXED)
                    device.disable_checksum()
                    device.set_symbol_rate_baud(transmission.symbol_rate)
                    device.set_output_power((0, 0xC0))
                    for packet in transmission.packets:
                        device.set_packet_length_bytes(len(packet))
                        started = time.monotonic()
                        device.transmit(packet)
                        while True:
                            # cc1101 3.0.0's state enum omits valid transient states.
                            state = device._read_status_register(Status.MARCSTATE) & 0x1F
                            if state == 1:  # IDLE: entire packet has left the radio.
                                break
                            if state == 22:  # TXFIFO_UNDERFLOW
                                raise RadioError('CC1101 transmit FIFO underflow')
                            if time.monotonic() - started >= 1.0:
                                raise RadioError('CC1101 transmit completion timed out')
                            time.sleep(0.001)
                        delay = transmission.minimum_interval - (time.monotonic() - started)
                        if delay > 0:
                            time.sleep(delay)
                finally:
                    try:
                        device._command_strobe(Strobe.SIDLE)
                    except Exception:
                        logger.exception('Could not restore radio to idle')
                        raise RadioError('Could not restore radio to idle')
        except RadioError:
            raise
        except Exception as exc:
            raise RadioError('CC1101 transmission failed') from exc
