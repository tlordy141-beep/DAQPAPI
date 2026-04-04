"""
basic_read.py — read all channels and display physical units.

Run from the project root with the venv active:
    python examples/basic_read.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daq.device import DT9805Device
from daq.reader import read_all_voltages, read_all_physical


def main():
    with DT9805Device() as dev:
        voltages = read_all_voltages(dev)
        physical = read_all_physical(dev)

    # --- Raw voltages ---
    print(f"\n{'Sensor':<8}  {'Raw voltage (V)':>16}")
    print("-" * 28)
    for name, v in voltages.items():
        print(f"{name:<8}  {v:>+16.6f}")

    # --- Physical readings ---
    print(f"\n{'Sensor':<8}  {'Physical value':>20}  {'Unit'}")
    print("-" * 42)
    for name, value in physical.items():
        if name == "CJC":
            unit, fmt = "°C (ambient)", f"{value:>+.2f}"
        elif name.startswith("TC"):
            unit = "°C"
            fmt  = f"{value:>+.2f}" if value is not None else "    DISCONNECTED"
        else:  # PT
            unit = "bar (gauge)"
            fmt  = f"{value:>+.3f}" if value is not None else "    DISCONNECTED"
        print(f"{name:<8}  {fmt:>20}  {unit}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)
