"""
channels.py — channel configuration for the DT9805.

Edit CHANNEL_CONFIG to change sensor assignments, gains, or add/remove channels.
The rest of the code reads from this list; nothing else needs changing.

Gain → voltage range (DT9805 specs):
    gain=1   → ±10.0 V  (305 µV/count at 16-bit)
    gain=10  →  ±1.0 V  ( 30 µV/count)
    gain=100 →  ±0.1 V  (  3 µV/count)  ← good for thermocouples (≈0–20 mV signal)
    gain=500 → ±0.02 V  (0.6 µV/count)

PT sensors (4–20 mA through 240 Ω shunt):
    I_min = 4  mA → V = 0.004 × 240 = 0.96 V
    I_max = 20 mA → V = 0.020 × 240 = 4.80 V
    gain=1 (±10 V range) covers this comfortably.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelConfig:
    """Configuration for one physical DAQ channel."""
    channel_id:  int    # Hardware channel index on the DT9805 (AI0 = CJC, AI1–AI7 = sensors)
    sensor_name: str    # Human-readable label (e.g. "TC1", "PT2")
    sensor_type: str    # "TC" for thermocouple, "PT" for pressure transducer
    gain:        float  # DT9805 gain setting (1, 10, 100, or 500)


# ---------------------------------------------------------------------------
# Channel assignments  (edit here to reconfigure)
# ---------------------------------------------------------------------------
CHANNEL_CONFIG: list[ChannelConfig] = [
    # Thermocouples — T-type, signal ≈ 0–20 mV → gain=100 (±0.1 V range)
    ChannelConfig(channel_id=1, sensor_name="TC1", sensor_type="TC", gain=100),
    ChannelConfig(channel_id=2, sensor_name="TC2", sensor_type="TC", gain=100),
    ChannelConfig(channel_id=3, sensor_name="TC3", sensor_type="TC", gain=100),

    # Pressure transducers — 4–20 mA / 240 Ω → 0.96–4.8 V → gain=1 (±10 V range)
    ChannelConfig(channel_id=4, sensor_name="PT1", sensor_type="PT", gain=1),
    ChannelConfig(channel_id=5, sensor_name="PT2", sensor_type="PT", gain=1),
    ChannelConfig(channel_id=6, sensor_name="PT3", sensor_type="PT", gain=1),
    ChannelConfig(channel_id=7, sensor_name="PT4", sensor_type="PT", gain=1),
]

# CJC channel — built-in cold-junction compensation sensor (10 mV/°C).
# Not in CHANNEL_CONFIG because it is read separately for TC linearisation.
CJC_CHANNEL_ID = 0
CJC_GAIN       = 10   # 10 mV/°C → max ~450 mV at 45°C → gain=10 (±1 V range)
