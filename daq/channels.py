"""
channels.py — ChannelConfig dataclass.

This module defines the data structure used to describe a sensor channel.
The actual channel list and all hardware constants are in config_hardware.py
at the project root — edit that file to change sensor assignments or gains.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelConfig:
    """
    Describes one analog input channel on the DT9805.

    Attributes
    ----------
    channel_id  : int   — hardware AI index (0 = CJC built-in, 1–7 = AI1–AI7)
    sensor_name : str   — short label used in CSV headers and plots (e.g. "TC1")
    sensor_type : str   — "TC" (thermocouple) or "PT" (pressure transducer)
    gain        : float — DAQ programmable gain:
                            1   → ±10 V input range
                            10  → ±1 V
                            100 → ±0.1 V  (thermocouple signals ≈ 0–20 mV)
                            500 → ±0.02 V
    """
    channel_id:  int
    sensor_name: str
    sensor_type: str
    gain:        float
