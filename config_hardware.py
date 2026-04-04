"""
config_hardware.py — hardware channel definitions and physical sensor constants.

Edit this file when the physical hardware setup changes:
  - New sensor installed or removed
  - DAQ channel reassigned
  - Gain changed
  - Shunt resistor replaced
  - Different pressure range sensor fitted

This file is read by:
  daq/reader.py       — CHANNEL_CONFIG, CJC settings
  sensors/pressure.py — PT transducer physical constants
"""
from daq.channels import ChannelConfig

# ---------------------------------------------------------------------------
# Analog input channel definitions
# ---------------------------------------------------------------------------
# Each entry describes one sensor wired into the DT9805.
#
# Fields:
#   channel_id  — hardware AI channel index  (0 = CJC built-in, 1–7 = AI1–AI7)
#   sensor_name — label used in CSV headers, plots, and config_run.py
#   sensor_type — "TC" (T-type thermocouple) or "PT" (4–20 mA pressure transducer)
#   gain        — DAQ programmable gain:
#                   gain=1   → ADC input range ±10 V
#                   gain=10  → ADC input range ±1 V
#                   gain=100 → ADC input range ±0.1 V  ← TC signals (~20 mV full scale)
#                   gain=500 → ADC input range ±0.02 V
#
CHANNEL_CONFIG: list[ChannelConfig] = [
    ChannelConfig(channel_id=1, sensor_name="TC1", sensor_type="TC", gain=100),
    ChannelConfig(channel_id=2, sensor_name="TC2", sensor_type="TC", gain=100),
    ChannelConfig(channel_id=3, sensor_name="TC3", sensor_type="TC", gain=100),
    ChannelConfig(channel_id=4, sensor_name="PT1", sensor_type="PT", gain=1),
    ChannelConfig(channel_id=5, sensor_name="PT2", sensor_type="PT", gain=1),
    ChannelConfig(channel_id=6, sensor_name="PT3", sensor_type="PT", gain=1),
    ChannelConfig(channel_id=7, sensor_name="PT4", sensor_type="PT", gain=1),
]

# ---------------------------------------------------------------------------
# Cold-junction compensation (CJC) sensor
# ---------------------------------------------------------------------------
# The DT9805 has an on-board CJC temperature sensor on AI0 (output: 10 mV/°C).
# gain=10 gives an ADC range of ±1 V, which covers −100°C to +100°C connector temp.
# This channel is always read automatically — do not add it to CHANNEL_CONFIG.
#
CJC_CHANNEL_ID: int   = 0
CJC_GAIN:       float = 10.0

# ---------------------------------------------------------------------------
# Pressure transducer (PT) physical constants
# ---------------------------------------------------------------------------
# All PT channels use a 4–20 mA current loop wired through a shunt resistor.
# The resulting voltage is what the DAQ measures:
#   I_MIN_MA × SHUNT_OHMS = voltage at 0 bar  (live-zero)
#   I_MAX_MA × SHUNT_OHMS = voltage at P_MAX_BAR
#
SHUNT_OHMS: float = 240.0   # Ω  — shunt resistor value (same on all PT channels)
I_MIN_MA:   float = 4.0     # mA — loop current at 0 bar (live-zero)
I_MAX_MA:   float = 20.0    # mA — loop current at full-scale pressure
P_MAX_BAR:  float = 40.0    # bar — full-scale gauge pressure of the transducers
