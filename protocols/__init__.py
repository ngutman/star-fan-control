"""Pure encoders: no SPI access or physical transmissions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Transmission:
    packets: tuple[bytes, ...]
    symbol_rate: int = 3300
    minimum_interval: float = 0.0
