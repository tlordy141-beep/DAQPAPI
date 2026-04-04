"""
pressure.py — 4–20 mA pressure transducer linearisation.

Hardware setup:
  - Sensor output : 4–20 mA current loop (proportional to 0–40 bar gauge)
  - Shunt resistor: 240 Ω  (converts current to voltage for the DAQ)
  - Resulting voltage range:
      4  mA × 240 Ω = 0.960 V  →  0 bar
      20 mA × 240 Ω = 4.800 V  →  40 bar

Conversion steps:
  1. Voltage → current:  I (mA) = V / 240 × 1000
  2. Current → pressure: P (bar) = (I − 4) / (20 − 4) × 40

  Combined:  P = (V − 0.960) / (4.800 − 0.960) × 40
"""

# --- Sensor and wiring constants (edit here if hardware changes) ---
SHUNT_OHMS = 240.0   # Ω — shunt resistor
I_MIN_MA   = 4.0     # mA — current at 0 bar (live-zero)
I_MAX_MA   = 20.0    # mA — current at full-scale pressure
P_MAX_BAR  = 40.0    # bar — full-scale pressure (gauge / relative)

# Derived voltage limits
V_MIN = I_MIN_MA  / 1000 * SHUNT_OHMS   # 0.960 V — sensor live at 0 bar
V_MAX = I_MAX_MA  / 1000 * SHUNT_OHMS   # 4.800 V — sensor at full scale


def pt_voltage_to_bar(voltage_v: float) -> float:
    """
    Convert shunt voltage from a 4–20 mA pressure transducer to bar (gauge).

    Parameters
    ----------
    voltage_v : float
        Voltage across the 240 Ω shunt resistor in volts, gain-corrected.
        Expected range: 0.960 V (0 bar) to 4.800 V (40 bar).

    Returns
    -------
    float : pressure in bar (gauge / relative).

    Notes
    -----
    Values below 0.960 V indicate < 4 mA, meaning the sensor is unpowered
    or disconnected. This returns a negative value so the caller can detect it.
    Values above 4.800 V indicate the sensor is over-range.
    """
    current_ma = voltage_v / SHUNT_OHMS * 1000               # V → mA
    pressure   = (current_ma - I_MIN_MA) / (I_MAX_MA - I_MIN_MA) * P_MAX_BAR
    return pressure


def sensor_status(voltage_v: float) -> str:
    """
    Return a human-readable status string for a PT channel.

    Returns
    -------
    str : "OK", "UNPOWERED/DISCONNECTED", or "OVER-RANGE"
    """
    if voltage_v < V_MIN * 0.9:   # allow 10% tolerance below live-zero
        return "UNPOWERED/DISCONNECTED"
    if voltage_v > V_MAX * 1.05:  # allow 5% tolerance above full-scale
        return "OVER-RANGE"
    return "OK"
