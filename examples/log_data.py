"""
log_data.py — continuous data logger.

Reads all channels at a fixed interval, prints a live table to the terminal,
and saves every sample to a timestamped CSV file in the data/ folder.

Usage:
    python examples/log_data.py                    # 1 s interval (default)
    python examples/log_data.py --interval 0.5     # 0.5 s interval
    python examples/log_data.py --output my_run.csv

Press Ctrl+C to stop logging.
"""
import sys
import os
import csv
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daq.device   import DT9805Device
from daq.reader   import read_all_physical
from daq.channels import CHANNEL_CONFIG

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _make_output_path() -> str:
    """Return a timestamped path inside the project's data/ folder."""
    data_dir = os.path.join(_PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(data_dir, f"{stamp}.csv")


def _sensor_names() -> list[str]:
    """Return sensor names in log order: CJC first, then channel config order."""
    return ["CJC"] + [ch.sensor_name for ch in CHANNEL_CONFIG]


def _format_value(sensor_name: str, value: float | None) -> str:
    """Format a physical value for terminal display."""
    if value is None:
        return "DISCONNECTED"
    if sensor_name == "CJC" or sensor_name.startswith("TC"):
        return f"{value:+.2f} \u00b0C"
    return f"{value:+.3f} bar"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Log DT9805 data to CSV.")
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Sampling interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output CSV path (default: data/YYYYMMDD_HHMMSS.csv)",
    )
    args = parser.parse_args()

    output_path  = args.output or _make_output_path()
    sensor_names = _sensor_names()
    header       = ["timestamp", "elapsed_s"] + sensor_names

    print(f"Output : {output_path}")
    print(f"Interval: {args.interval} s")
    print("Press Ctrl+C to stop.\n")

    COL_W = 20   # terminal column width per sensor

    try:
        with DT9805Device() as dev, \
             open(output_path, "w", newline="") as csv_file:

            writer = csv.writer(csv_file)
            writer.writerow(header)
            csv_file.flush()

            t0      = time.monotonic()
            sample  = 0

            while True:
                t_read   = time.monotonic()
                physical = read_all_physical(dev)
                elapsed  = t_read - t0
                timestamp = datetime.now().isoformat(sep=" ", timespec="milliseconds")

                # --- Write CSV row (empty string for None / disconnected) ---
                row = [timestamp, f"{elapsed:.3f}"]
                for sn in sensor_names:
                    v = physical.get(sn)
                    row.append("" if v is None else f"{v:.4f}")
                writer.writerow(row)
                csv_file.flush()

                # --- Terminal table (reprint header every 20 rows) ---
                sample += 1
                if sample == 1 or sample % 20 == 0:
                    hdr_line = (
                        f"  {'time':>12}  {'elapsed':>9}  " +
                        "  ".join(f"{sn:>{COL_W}}" for sn in sensor_names)
                    )
                    print(hdr_line)
                    print("  " + "-" * (12 + 2 + 9 + 2 + (COL_W + 2) * len(sensor_names)))

                data_line = (
                    f"  {timestamp[-12:]:>12}  {elapsed:>9.3f}  " +
                    "  ".join(
                        f"{_format_value(sn, physical.get(sn)):>{COL_W}}"
                        for sn in sensor_names
                    )
                )
                print(data_line)

                # Sleep for the remainder of the interval
                sleep_time = args.interval - (time.monotonic() - t_read)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\nStopped.  {sample} samples written to {output_path}")
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
