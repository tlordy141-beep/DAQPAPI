"""
log_and_plot.py — continuous data logger with optional real-time plot.

Reads the channels listed in config_run.py at a fixed interval, prints a live
table to the terminal, saves every sample to a timestamped CSV file, and
optionally shows a live matplotlib plot that updates each sample.

Configuration: edit config_run.py before running.
Hardware setup: edit config_hardware.py when physical connections change.

Run from the project root with the venv active:
    python scripts/log_and_plot.py

Press Ctrl+C to stop logging.
"""
import sys
import os
import csv
import time
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import config_run
from daq.device        import DT9805Device
from daq.reader        import validate_active_channels, read_all_physical, ordered_sensor_names
from analysis.plotting import LivePlot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_output_path() -> str:
    """Return a timestamped CSV path inside the project's data/ folder."""
    data_dir = os.path.join(_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")


def _format_value(sensor_name: str, value: float | None) -> str:
    """Format a physical value for the terminal table."""
    if value is None:
        return "DISCONNECTED"
    if sensor_name == "CJC" or sensor_name.startswith("TC"):
        return f"{value:+.2f} \u00b0C"
    return f"{value:+.3f} bar"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # --- Read and validate config ---
    active   = validate_active_channels(config_run.ACTIVE_CHANNELS)
    out_path = config_run.OUTPUT_PATH or _make_output_path()
    interval = config_run.SAMPLE_INTERVAL_S
    names    = ordered_sensor_names(active)   # ["CJC", "TC1", ..., "PT1", ...]
    header   = ["timestamp", "elapsed_s"] + names

    print(f"Active channels : {sorted(active)}")
    print(f"Output          : {out_path}")
    print(f"Interval        : {interval} s")
    print(f"Live plot       : {'yes' if config_run.LIVE_PLOT else 'no'}")
    print("Press Ctrl+C to stop.\n")

    # --- Initialise live plot before opening hardware ---
    # Doing this first lets the window appear and be positioned by the user
    # before the DAQ connection opens.
    live_plot = (
        LivePlot(
            sensor_names=names,
            figsize=config_run.PLOT_FIGSIZE,
            colors=config_run.PLOT_COLORS,
            line_width=config_run.PLOT_LINE_WIDTH,
        )
        if config_run.LIVE_PLOT else None
    )

    COL_W  = 20
    sample = 0

    try:
        with DT9805Device() as dev, open(out_path, "w", newline="") as csv_file:

            writer = csv.writer(csv_file)
            writer.writerow(header)
            csv_file.flush()

            t0 = time.monotonic()

            while True:
                t_read    = time.monotonic()
                physical  = read_all_physical(dev, active=active)
                elapsed   = t_read - t0
                timestamp = datetime.now().isoformat(sep=" ", timespec="milliseconds")

                # --- Write CSV row ---
                row = [timestamp, f"{elapsed:.3f}"]
                for n in names:
                    v = physical.get(n)
                    row.append("" if v is None else f"{v:.4f}")
                writer.writerow(row)
                csv_file.flush()

                # --- Update live plot ---
                if live_plot is not None:
                    live_plot.update(elapsed, physical)

                # --- Print terminal table ---
                sample += 1
                if sample == 1 or sample % 20 == 0:
                    print(
                        f"  {'time':>12}  {'elapsed':>9}  " +
                        "  ".join(f"{n:>{COL_W}}" for n in names)
                    )
                    print("  " + "-" * (12 + 2 + 9 + 2 + (COL_W + 2) * len(names)))

                print(
                    f"  {timestamp[-12:]:>12}  {elapsed:>9.3f}  " +
                    "  ".join(
                        f"{_format_value(n, physical.get(n)):>{COL_W}}"
                        for n in names
                    )
                )

                # --- Sleep for the remainder of the interval ---
                sleep_time = interval - (time.monotonic() - t_read)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\nStopped.  {sample} samples written to {out_path}")
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)
    finally:
        if live_plot is not None:
            live_plot.destroy()


if __name__ == "__main__":
    main()
