"""
reader.py — reads configured channels in one pass and converts to physical units.

Public API
----------
validate_active_channels(active)   — check names against config_hardware; returns set
ordered_sensor_names(active)       — ["CJC"] + active channels in config order
read_all_voltages(device, active)  — raw voltages for active channels (V)
read_all_physical(device, active)  — physical units: °C for TC/CJC, bar for PT

The `active` parameter is a set[str] of sensor_name values from config_hardware.py.
Pass None to read all configured channels (default, backward-compatible).

Channel configuration and physical constants are imported from config_hardware.py.
"""
import os
import sys

# Ensure the project root is on sys.path so config_hardware.py is importable
# when this module is used directly (e.g. in tests or interactive sessions).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_hardware import CHANNEL_CONFIG, CJC_CHANNEL_ID, CJC_GAIN
from daq.device import DT9805Device


# ---------------------------------------------------------------------------
# Validation and ordering
# ---------------------------------------------------------------------------

def validate_active_channels(active: list[str]) -> set[str]:
    """
    Check every name in `active` exists in CHANNEL_CONFIG.

    Raises ValueError immediately (before any hardware is touched) if an
    unrecognised name is found — catches typos in config_run.py early.

    Parameters
    ----------
    active : list[str]
        The ACTIVE_CHANNELS list from config_run.py.

    Returns
    -------
    set[str] : the same names as a set, for fast O(1) membership tests.
    """
    valid = {ch.sensor_name for ch in CHANNEL_CONFIG}
    bad   = [n for n in active if n not in valid]
    if bad:
        raise ValueError(
            f"config_run.ACTIVE_CHANNELS contains unrecognised name(s): {bad}\n"
            f"Valid names from config_hardware.py: {sorted(valid)}"
        )
    return set(active)


def ordered_sensor_names(active: set[str]) -> list[str]:
    """
    Return the display/CSV column order for a set of active channels.

    Always ["CJC"] first, then active channels in the order they appear
    in CHANNEL_CONFIG (i.e. channel_id order, TC before PT).

    Parameters
    ----------
    active : set[str]

    Returns
    -------
    list[str] : e.g. ["CJC", "TC1", "TC2", "PT1", "PT3"]
    """
    return ["CJC"] + [ch.sensor_name for ch in CHANNEL_CONFIG if ch.sensor_name in active]


# ---------------------------------------------------------------------------
# Hardware reads
# ---------------------------------------------------------------------------

def read_all_voltages(
    device: DT9805Device,
    active: set[str] | None = None,
) -> dict[str, float]:
    """
    Read one voltage sample from each active channel, plus CJC.

    Parameters
    ----------
    device : DT9805Device
        An already-opened device instance.
    active : set[str] | None
        Sensor names to read.  None = read all channels in CHANNEL_CONFIG.
        CJC is always read regardless of this parameter.

    Returns
    -------
    dict[str, float] : sensor_name → voltage in volts.  "CJC" is always present.
    """
    readings: dict[str, float] = {}
    for ch in CHANNEL_CONFIG:
        if active is None or ch.sensor_name in active:
            readings[ch.sensor_name] = device.read_voltage(ch.channel_id, ch.gain)
    readings["CJC"] = device.read_voltage(CJC_CHANNEL_ID, CJC_GAIN)
    return readings


def read_all_physical(
    device: DT9805Device,
    active: set[str] | None = None,
) -> dict[str, float | None]:
    """
    Read active channels and return values in physical units.

    TC  channels → temperature in °C  (via NIST ITS-90 T-type polynomial + CJC)
    PT  channels → pressure in bar gauge  (via 4–20 mA linearisation)
    CJC          → connector temperature in °C  (always present)

    A channel returns None if conversion fails — typically a disconnected or
    out-of-range thermocouple.

    Parameters
    ----------
    device : DT9805Device
        An already-opened device instance.
    active : set[str] | None
        Sensor names to read.  None = read all channels.

    Returns
    -------
    dict[str, float | None] : sensor_name → physical value or None.
    """
    from sensors.thermocouple import tc_voltage_to_celsius, cjc_voltage_to_celsius
    from sensors.pressure     import pt_voltage_to_bar

    voltages   = read_all_voltages(device, active=active)
    cjc_temp_c = cjc_voltage_to_celsius(voltages["CJC"])

    physical: dict[str, float | None] = {"CJC": cjc_temp_c}

    for ch in CHANNEL_CONFIG:
        if active is not None and ch.sensor_name not in active:
            continue
        v = voltages[ch.sensor_name]
        if ch.sensor_type == "TC":
            try:
                physical[ch.sensor_name] = tc_voltage_to_celsius(v, cjc_temp_c)
            except ValueError:
                physical[ch.sensor_name] = None   # disconnected or out of range
        elif ch.sensor_type == "PT":
            physical[ch.sensor_name] = pt_voltage_to_bar(v)

    return physical
