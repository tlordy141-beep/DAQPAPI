"""
02_log_data.py — continuous data logger with optional real-time plot.

Reads the channels listed in config.py at a fixed interval, prints a live
table to the terminal, saves every sample to a CSV file, and optionally
shows a live matplotlib plot that updates each sample.

Configuration is read from config.py at the project root — edit that file
before running this script.

Run from the project root with the venv active:
    python examples/02_log_data.py

Press Ctrl+C to stop logging.
"""
import sys
import os
import csv
import time
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import config
from daq.device   import DT9805Device
from daq.reader   import read_all_physical
from daq.channels import CHANNEL_CONFIG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_active_channels(active: list[str]) -> set[str]:
    """
    Check every name in active exists in CHANNEL_CONFIG.
    Raises ValueError immediately (before any hardware is touched) if not.
    """
    valid = {ch.sensor_name for ch in CHANNEL_CONFIG}
    bad   = [n for n in active if n not in valid]
    if bad:
        raise ValueError(
            f"config.ACTIVE_CHANNELS contains unrecognised name(s): {bad}\n"
            f"Valid sensor names are: {sorted(valid)}"
        )
    return set(active)


def _make_output_path() -> str:
    """Return a timestamped CSV path inside the project's data/ folder."""
    data_dir = os.path.join(_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(data_dir, f"{stamp}.csv")


def _sensor_names_ordered(active: set[str]) -> list[str]:
    """CJC first, then active sensors in CHANNEL_CONFIG order."""
    return ["CJC"] + [
        ch.sensor_name for ch in CHANNEL_CONFIG
        if ch.sensor_name in active
    ]


def _format_value(sensor_name: str, value: float | None) -> str:
    """Format a physical value for terminal display."""
    if value is None:
        return "DISCONNECTED"
    if sensor_name == "CJC" or sensor_name.startswith("TC"):
        return f"{value:+.2f} \u00b0C"
    return f"{value:+.3f} bar"


# ---------------------------------------------------------------------------
# Real-time plot
# ---------------------------------------------------------------------------

class _LivePlot:
    """
    Manages the live matplotlib plot shown during logging.

    The plot is created with plt.ion() (interactive mode).  Each call to
    update() redraws the lines and calls plt.pause(0.001) to flush GUI
    events — this is what keeps the window responsive and redraws the data.

    If the user closes the window, is_open returns False and update()
    becomes a no-op, so logging continues uninterrupted.
    """

    def __init__(self, active: set[str]) -> None:
        import matplotlib
        matplotlib.use("TkAgg")   # explicit backend for reliable Windows behaviour
        import matplotlib.pyplot as plt
        self._plt = plt

        self._tc_names = [
            ch.sensor_name for ch in CHANNEL_CONFIG
            if ch.sensor_name in active and ch.sensor_type == "TC"
        ]
        self._pt_names = [
            ch.sensor_name for ch in CHANNEL_CONFIG
            if ch.sensor_name in active and ch.sensor_type == "PT"
        ]

        self._lines:   dict[str, object] = {}
        self._data:    dict[str, list]   = {}
        self._elapsed: list[float]       = []
        self._fig  = None
        self._ax_tc = None
        self._ax_pt = None

        self._build()

    def _build(self) -> None:
        plt = self._plt
        plt.ion()

        show_tc = bool(self._tc_names)
        show_pt = bool(self._pt_names)
        n_plots = show_tc + show_pt

        if n_plots == 0:
            return

        if n_plots == 2:
            self._fig, (self._ax_tc, self._ax_pt) = plt.subplots(
                2, 1, figsize=(10, 6), sharex=True
            )
            self._fig.subplots_adjust(hspace=0.08)
        elif show_tc:
            self._fig, self._ax_tc = plt.subplots(1, 1, figsize=(10, 4))
        else:
            self._fig, self._ax_pt = plt.subplots(1, 1, figsize=(10, 4))

        self._fig.suptitle(
            "Live DAQ readings  \u2014  close window to keep logging without plot",
            fontsize=10,
        )

        if self._ax_tc is not None:
            for name in self._tc_names:
                (line,) = self._ax_tc.plot([], [], label=name, linewidth=1.4)
                self._lines[name] = line
                self._data[name]  = []
            # CJC as dashed grey reference line on the TC subplot
            (line,) = self._ax_tc.plot(
                [], [], label="CJC (ambient)",
                linewidth=1.0, linestyle="--", color="grey", alpha=0.7,
            )
            self._lines["CJC"] = line
            self._data["CJC"]  = []
            self._ax_tc.set_ylabel("Temperature (\u00b0C)")
            self._ax_tc.legend(loc="upper right", fontsize=9)
            self._ax_tc.grid(True, alpha=0.35)

        if self._ax_pt is not None:
            for name in self._pt_names:
                (line,) = self._ax_pt.plot([], [], label=name, linewidth=1.4)
                self._lines[name] = line
                self._data[name]  = []
            self._ax_pt.axhline(0, color="black", linewidth=0.8,
                                linestyle=":", label="0 bar")
            self._ax_pt.set_ylabel("Pressure (bar gauge)")
            self._ax_pt.set_xlabel("Elapsed time (s)")
            self._ax_pt.legend(loc="upper right", fontsize=9)
            self._ax_pt.grid(True, alpha=0.35)

        plt.tight_layout()
        plt.pause(0.001)   # initial draw so window appears before first sample

    @property
    def is_open(self) -> bool:
        """True while the figure window is open."""
        if self._fig is None:
            return False
        return self._plt.fignum_exists(self._fig.number)

    def update(self, elapsed_s: float, physical: dict) -> None:
        """Append one sample and redraw.  No-op if the window has been closed."""
        if not self.is_open:
            return

        self._elapsed.append(elapsed_s)

        for name, line in self._lines.items():
            value = physical.get(name)
            self._data[name].append(float("nan") if value is None else value)
            line.set_xdata(self._elapsed)
            line.set_ydata(self._data[name])

        for ax in (self._ax_tc, self._ax_pt):
            if ax is not None:
                ax.relim()
                ax.autoscale_view()

        self._plt.pause(0.001)   # flushes GUI event queue; keeps window responsive

    def destroy(self) -> None:
        """Close the figure if it is still open."""
        if self.is_open:
            self._plt.close(self._fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Validate config before touching hardware
    active       = _validate_active_channels(config.ACTIVE_CHANNELS)
    out_path     = config.OUTPUT_PATH or _make_output_path()
    interval     = config.SAMPLE_INTERVAL_S
    sensor_names = _sensor_names_ordered(active)
    header       = ["timestamp", "elapsed_s"] + sensor_names

    print(f"Active channels : {sorted(active)}")
    print(f"Output          : {out_path}")
    print(f"Interval        : {interval} s")
    print(f"Live plot       : {'yes' if config.LIVE_PLOT else 'no'}")
    print("Press Ctrl+C to stop.\n")

    # Initialise the plot before opening hardware so the window appears first
    live_plot = _LivePlot(active) if config.LIVE_PLOT else None

    COL_W  = 20
    sample = 0

    try:
        with DT9805Device() as dev, \
             open(out_path, "w", newline="") as csv_file:

            writer = csv.writer(csv_file)
            writer.writerow(header)
            csv_file.flush()

            t0 = time.monotonic()

            while True:
                t_read    = time.monotonic()
                physical  = read_all_physical(dev, active=active)
                elapsed   = t_read - t0
                timestamp = datetime.now().isoformat(sep=" ", timespec="milliseconds")

                # --- CSV row ---
                row = [timestamp, f"{elapsed:.3f}"]
                for sn in sensor_names:
                    v = physical.get(sn)
                    row.append("" if v is None else f"{v:.4f}")
                writer.writerow(row)
                csv_file.flush()

                # --- Live plot ---
                if live_plot is not None:
                    live_plot.update(elapsed, physical)

                # --- Terminal table ---
                sample += 1
                if sample == 1 or sample % 20 == 0:
                    hdr = (
                        f"  {'time':>12}  {'elapsed':>9}  " +
                        "  ".join(f"{sn:>{COL_W}}" for sn in sensor_names)
                    )
                    print(hdr)
                    print("  " + "-" * (12 + 2 + 9 + 2 + (COL_W + 2) * len(sensor_names)))

                print(
                    f"  {timestamp[-12:]:>12}  {elapsed:>9.3f}  " +
                    "  ".join(
                        f"{_format_value(sn, physical.get(sn)):>{COL_W}}"
                        for sn in sensor_names
                    )
                )

                # Sleep for the remainder of the interval
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
