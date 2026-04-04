"""
01_basic_read.py — read all active channels once and display physical units.

Configuration is read from config.py at the project root.

Run from the project root with the venv active:
    python examples/01_basic_read.py
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import config
from daq.device   import DT9805Device
from daq.reader   import read_all_voltages, read_all_physical
from daq.channels import CHANNEL_CONFIG


def _validate_active_channels(active: list[str]) -> set[str]:
    valid = {ch.sensor_name for ch in CHANNEL_CONFIG}
    bad   = [n for n in active if n not in valid]
    if bad:
        raise ValueError(
            f"config.ACTIVE_CHANNELS contains unrecognised name(s): {bad}\n"
            f"Valid sensor names are: {sorted(valid)}"
        )
    return set(active)


def main():
    active = _validate_active_channels(config.ACTIVE_CHANNELS)

    with DT9805Device() as dev:
        voltages = read_all_voltages(dev, active=active)
        physical = read_all_physical(dev, active=active)

    # Ordered display: CJC first, then active channels in config order
    sensor_names = ["CJC"] + [
        ch.sensor_name for ch in CHANNEL_CONFIG if ch.sensor_name in active
    ]

    # --- Raw voltages ---
    print(f"\n{'Sensor':<8}  {'Raw voltage (V)':>16}")
    print("-" * 28)
    for name in sensor_names:
        v = voltages.get(name)
        if v is not None:
            print(f"{name:<8}  {v:>+16.6f}")

    # --- Physical readings ---
    print(f"\n{'Sensor':<8}  {'Physical value':>20}  {'Unit'}")
    print("-" * 42)
    for name in sensor_names:
        value = physical.get(name)
        if name == "CJC":
            unit = "\u00b0C (ambient)"
            fmt  = f"{value:>+.2f}" if value is not None else "    ERROR"
        elif name.startswith("TC"):
            unit = "\u00b0C"
            fmt  = f"{value:>+.2f}" if value is not None else "    DISCONNECTED"
        else:  # PT
            unit = "bar (gauge)"
            fmt  = f"{value:>+.3f}" if value is not None else "    DISCONNECTED"
        print(f"{name:<8}  {fmt:>20}  {unit}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)
