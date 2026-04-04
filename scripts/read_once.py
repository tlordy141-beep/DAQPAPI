"""
read_once.py — read all active channels once and display physical units.

A quick sanity check to confirm the hardware is connected and all active
sensors are responding with plausible values before starting a logging run.

Configuration: edit config_run.py (ACTIVE_CHANNELS).

Run from the project root with the venv active:
    python scripts/read_once.py
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import config_run
from config_hardware     import CHANNEL_CONFIG
from daq.device          import DT9805Device
from daq.reader          import validate_active_channels, read_all_voltages, read_all_physical


def main():
    active = validate_active_channels(config_run.ACTIVE_CHANNELS)
    names  = ["CJC"] + [ch.sensor_name for ch in CHANNEL_CONFIG if ch.sensor_name in active]

    with DT9805Device() as dev:
        voltages = read_all_voltages(dev, active=active)
        physical = read_all_physical(dev, active=active)

    # --- Raw voltages ---
    print(f"\n{'Channel':<8}  {'Raw voltage (V)':>16}")
    print("-" * 28)
    for name in names:
        v = voltages.get(name)
        if v is not None:
            print(f"{name:<8}  {v:>+16.6f}")

    # --- Physical readings ---
    print(f"\n{'Channel':<8}  {'Value':>20}  Unit")
    print("-" * 44)
    for name in names:
        val = physical.get(name)
        if name == "CJC":
            unit = "\u00b0C (ambient)"
            fmt  = f"{val:>+.2f}" if val is not None else "    ERROR"
        elif name.startswith("TC"):
            unit = "\u00b0C"
            fmt  = f"{val:>+.2f}" if val is not None else "    DISCONNECTED"
        else:
            unit = "bar (gauge)"
            fmt  = f"{val:>+.3f}" if val is not None else "    DISCONNECTED"
        print(f"{name:<8}  {fmt:>20}  {unit}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)
