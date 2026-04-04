"""
pressure.py — 4–20 mA pressure transducer linearisation.

Physical constants (shunt resistor, current range, pressure range) are
imported from config_hardware.py so they are configured in one place.

Conversion steps:
  1. Voltage → current:  I (mA) = V / SHUNT_OHMS × 1000
  2. Current → pressure: P (bar) = (I − I_MIN_MA) / (I_MAX_MA − I_MIN_MA) × P_MAX_BAR

  Combined:  P = (V − V_MIN) / (V_MAX − V_MIN) × P_MAX_BAR
"""
import os
import sys

# Ensure the project root is on sys.path so config_hardware.py is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_hardware import SHUNT_OHMS, I_MIN_MA, I_MAX_MA, P_MAX_BAR

# Derived voltage limits (computed once at import time)
V_MIN: float = I_MIN_MA / 1000 * SHUNT_OHMS   # 0.960 V — voltage at 0 bar (live-zero)
V_MAX: float = I_MAX_MA / 1000 * SHUNT_OHMS   # 4.800 V — voltage at full-scale pressure


def pt_voltage_to_bar(voltage_v: float) -> float:
    """
    Convert shunt voltage from a 4–20 mA pressure transducer to bar (gauge).

    Parameters
    ----------
    voltage_v : float
        Voltage across the shunt resistor in volts, gain-corrected by the DAQ.
        Expected range: V_MIN (0 bar) to V_MAX (P_MAX_BAR).

    Returns
    -------
    float : pressure in bar (gauge).

    Notes
    -----
    Values below V_MIN indicate less than I_MIN_MA — the sensor is unpowered
    or disconnected.  A negative pressure result is returned so the caller
    can detect it (rather than clamping to zero and hiding the fault).
    Values above V_MAX indicate over-range.
    """
    current_ma = voltage_v / SHUNT_OHMS * 1000
    return (current_ma - I_MIN_MA) / (I_MAX_MA - I_MIN_MA) * P_MAX_BAR


def sensor_status(voltage_v: float) -> str:
    """
    Return a human-readable status string for a PT channel.

    Returns
    -------
    str : one of "OK", "UNPOWERED/DISCONNECTED", "OVER-RANGE"
    """
    if voltage_v < V_MIN * 0.9:    # 10% tolerance below live-zero
        return "UNPOWERED/DISCONNECTED"
    if voltage_v > V_MAX * 1.05:   # 5% tolerance above full-scale
        return "OVER-RANGE"
    return "OK"
