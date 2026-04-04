"""
thermocouple.py — T-type thermocouple linearisation with cold-junction compensation.

T-type thermocouple (Copper / Constantan):
  - Sensitivity: ~39 µV/°C at 0°C, rising to ~60 µV/°C at 400°C
  - Usable range: −200°C to +400°C  (−5.603 mV to +20.872 mV)

All polynomial coefficients are from the NIST ITS-90 thermocouple reference:
  https://srdata.nist.gov/its90/main/

Cold-junction compensation (CJC) — why it is needed
----------------------------------------------------
A thermocouple measures the temperature DIFFERENCE between its hot junction
(measurement point) and its cold junction (the connector on the DAQ board).
The DT9805 has an on-board CJC temperature sensor (channel AI0, 10 mV/°C) so
we can measure the connector temperature and compensate for it.

Procedure:
  1. T_cold  = CJC sensor voltage / 0.010        (sensor: 10 mV/°C)
  2. V_cold  = tc_celsius_to_mv(T_cold)          (forward polynomial: °C → mV)
  3. V_total = V_measured_mv + V_cold            (add reference EMF back in)
  4. T_hot   = tc_mv_to_celsius(V_total)         (inverse polynomial: mV → °C)
"""

from numpy.polynomial.polynomial import polyval  # polyval(x, [c0, c1, c2, ...])

# ---------------------------------------------------------------------------
# NIST ITS-90  T-type inverse polynomial  (mV → °C)
# ---------------------------------------------------------------------------
# Range  −200°C to 0°C  (−5.603 mV to 0 mV)
_INV_NEG = [
     0.0000000E+00,   # c0
     2.5949192E+01,   # c1
    -2.1316967E-01,   # c2
     7.9018692E-01,   # c3
     4.2527777E-01,   # c4
     1.3304473E-01,   # c5
     2.0241446E-02,   # c6
     1.2668171E-03,   # c7
]

# Range  0°C to 400°C  (0 mV to 20.872 mV)
_INV_POS = [
     0.0000000E+00,   # c0
     2.5928000E+01,   # c1
    -7.6029610E-01,   # c2
     4.6377910E-02,   # c3
    -2.1653940E-03,   # c4
     6.0481440E-05,   # c5
    -7.2934220E-07,   # c6
]

# ---------------------------------------------------------------------------
# NIST ITS-90  T-type forward polynomial  (°C → mV)
# Used only for CJC compensation step 2.
# ---------------------------------------------------------------------------
# Range  −270°C to 0°C
_FWD_NEG = [
     0.00000000000000E+00,
     3.87481063640E-02,
     4.41944343470E-05,
     1.18434545390E-07,
     2.00329735590E-10,
     9.01380195590E-13,
     2.26513022120E-15,
     3.60711542050E-17,
     3.84939398830E-19,
     2.82135219230E-21,
     1.42515947790E-23,
     4.87686622800E-26,
     1.07955392700E-28,
     1.39450270600E-31,
     7.97951539200E-35,
]

# Range  0°C to 400°C
_FWD_POS = [
     0.00000000000000E+00,
     3.87481063640E-02,
     3.32922287800E-05,
     2.06182434040E-07,
    -2.18822568460E-09,
     1.09966004110E-11,
    -3.08157587720E-14,
     4.45638629830E-17,
    -2.65708780530E-20,
]

# Valid voltage range for T-type (mV)
_EMF_MIN_MV = -5.603
_EMF_MAX_MV = 20.872


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def cjc_voltage_to_celsius(cjc_voltage_v: float) -> float:
    """
    Convert the DT9805 on-board CJC sensor voltage to temperature.

    The CJC sensor outputs 10 mV per °C. device.py has already divided
    by the gain (CJC_GAIN = 10), so cjc_voltage_v is the actual sensor output.

    Parameters
    ----------
    cjc_voltage_v : float
        CJC voltage in volts, gain-corrected.

    Returns
    -------
    float : connector (ambient) temperature in °C.
    """
    return cjc_voltage_v / 0.010   # 10 mV/°C = 0.010 V/°C


def _celsius_to_mv(temp_c: float) -> float:
    """T-type forward polynomial: temperature (°C) → EMF (mV)."""
    coeffs = _FWD_NEG if temp_c <= 0 else _FWD_POS
    return float(polyval(temp_c, coeffs))


def _mv_to_celsius(emf_mv: float) -> float:
    """
    T-type inverse polynomial: EMF (mV) → temperature (°C).
    Raises ValueError if emf_mv is outside the valid T-type range.
    """
    if not (_EMF_MIN_MV <= emf_mv <= _EMF_MAX_MV):
        raise ValueError(
            f"TC EMF {emf_mv:.4f} mV is outside T-type range "
            f"({_EMF_MIN_MV} to {_EMF_MAX_MV} mV). "
            "Check that the sensor is connected and in range."
        )
    coeffs = _INV_NEG if emf_mv <= 0 else _INV_POS
    return float(polyval(emf_mv, coeffs))


def tc_voltage_to_celsius(tc_voltage_v: float, cjc_temp_c: float) -> float:
    """
    Convert a T-type thermocouple raw voltage to temperature, with CJC compensation.

    Parameters
    ----------
    tc_voltage_v : float
        Raw TC voltage in volts, gain-corrected by device.py.
    cjc_temp_c : float
        Cold junction temperature in °C, from cjc_voltage_to_celsius().

    Returns
    -------
    float : hot junction temperature in °C.

    Raises
    ------
    ValueError if the resulting EMF is out of the T-type voltage range,
    which usually means the sensor is disconnected or faulty.
    """
    tc_mv      = tc_voltage_v * 1000          # V → mV
    v_cold_mv  = _celsius_to_mv(cjc_temp_c)  # reference EMF for cold junction
    v_total_mv = tc_mv + v_cold_mv            # absolute EMF from 0°C reference
    return _mv_to_celsius(v_total_mv)
