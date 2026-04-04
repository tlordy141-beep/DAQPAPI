"""
reader.py — reads all configured channels in one pass.

Two functions are provided:
  read_all_voltages()  — raw voltages from every active channel (V)
  read_all_physical()  — converted physical units (°C and bar)

Both accept an optional `active` parameter — a set of sensor_name strings.
Pass None (the default) to read all channels, or a set to read only the
named channels. CJC is always read regardless of `active`.
"""
from daq.device   import DT9805Device
from daq.channels import CHANNEL_CONFIG, CJC_CHANNEL_ID, CJC_GAIN


def read_all_voltages(
    device: DT9805Device,
    active: set[str] | None = None,
) -> dict[str, float]:
    """
    Read one voltage sample from each active channel in CHANNEL_CONFIG, plus CJC.

    Parameters
    ----------
    device : DT9805Device
        An already-opened DT9805Device instance.
    active : set[str] | None
        Set of sensor_name strings to read.  None means read all channels.
        CJC is always read regardless of this parameter.

    Returns
    -------
    dict : sensor name (str) → voltage in volts (float).
           CJC reading is stored under the key "CJC".
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
    Read all active channels and return values in physical units.

    TC channels  → temperature in °C
    PT channels  → pressure in bar (gauge)
    CJC          → ambient temperature at connector in °C

    Returns None for a channel if conversion fails (e.g. sensor disconnected).

    Parameters
    ----------
    device : DT9805Device
        An already-opened DT9805Device instance.
    active : set[str] | None
        Set of sensor_name strings to read.  None means read all channels.
        CJC is always read and converted regardless of this parameter.

    Returns
    -------
    dict : sensor name (str) → physical value (float) or None if invalid.
    """
    from sensors.thermocouple import tc_voltage_to_celsius, cjc_voltage_to_celsius
    from sensors.pressure     import pt_voltage_to_bar

    voltages = read_all_voltages(device, active=active)

    # CJC must be converted first — TC linearisation depends on it
    cjc_temp_c = cjc_voltage_to_celsius(voltages["CJC"])
    physical: dict[str, float | None] = {"CJC": cjc_temp_c}

    for ch in CHANNEL_CONFIG:
        if active is not None and ch.sensor_name not in active:
            continue   # skip channels not requested
        v = voltages[ch.sensor_name]
        if ch.sensor_type == "TC":
            try:
                physical[ch.sensor_name] = tc_voltage_to_celsius(v, cjc_temp_c)
            except ValueError:
                physical[ch.sensor_name] = None   # disconnected or out of range
        elif ch.sensor_type == "PT":
            physical[ch.sensor_name] = pt_voltage_to_bar(v)

    return physical
