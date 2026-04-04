"""
plotting.py — load and plot CSV log files produced by log_data.py.

Functions
---------
load_csv(filepath)
    Load a log CSV into a dict of numpy arrays.
    Disconnected readings (empty cells) are stored as NaN so matplotlib
    simply leaves a gap in the line rather than crashing.

plot_all(data, title=None)
    Two-subplot figure: temperature channels on top, pressure on bottom.
    Pass either the dict from load_csv() or a file path string directly.
"""
import csv
import os
import numpy as np
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv(filepath: str) -> dict:
    """
    Load a log CSV file produced by log_data.py.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.

    Returns
    -------
    dict with keys:
        "timestamp"  — list of str  (ISO-format timestamp strings)
        "elapsed_s"  — numpy float64 array
        <sensor>     — numpy float64 array (NaN where sensor was disconnected)
    """
    with open(filepath, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows   = list(reader)

    if not rows:
        raise ValueError(f"CSV file is empty: {filepath}")

    data: dict = {}
    data["timestamp"] = [r[0] for r in rows]
    data["elapsed_s"] = np.array([float(r[1]) for r in rows])

    # Every column after "elapsed_s" is a sensor reading
    for i, name in enumerate(header[2:], start=2):
        values = []
        for row in rows:
            cell = row[i] if i < len(row) else ""
            values.append(float(cell) if cell else float("nan"))
        data[name] = np.array(values)

    return data


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_all(data, title: str = None) -> plt.Figure:
    """
    Plot temperature and pressure channels from logged data.

    Parameters
    ----------
    data : dict or str
        Either the dict returned by load_csv(), or a path to a CSV file.
        Passing a file path is a convenient shorthand.
    title : str, optional
        Figure title.  Defaults to the filename if data is a str.

    Returns
    -------
    matplotlib.figure.Figure
        The figure object — call plt.show() afterwards to display it.
    """
    if isinstance(data, str):
        title = title or os.path.basename(data)
        data  = load_csv(data)

    elapsed  = data["elapsed_s"]
    tc_names = [k for k in data if k.startswith("TC")]
    pt_names = [k for k in data if k.startswith("PT")]

    fig, (ax_tc, ax_pt) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    fig.subplots_adjust(hspace=0.08)

    if title:
        fig.suptitle(title, fontsize=10, y=0.99)

    # --- Temperature subplot ---
    for name in tc_names:
        ax_tc.plot(elapsed, data[name], label=name, linewidth=1.4)
    if "CJC" in data:
        ax_tc.plot(
            elapsed, data["CJC"],
            label="CJC (ambient)",
            linewidth=1.0, linestyle="--", color="grey", alpha=0.7,
        )
    ax_tc.set_ylabel("Temperature (\u00b0C)")
    ax_tc.legend(loc="upper right", fontsize=9)
    ax_tc.grid(True, alpha=0.35)

    # --- Pressure subplot ---
    for name in pt_names:
        ax_pt.plot(elapsed, data[name], label=name, linewidth=1.4)
    ax_pt.axhline(0, color="black", linewidth=0.8, linestyle=":", label="0 bar")
    ax_pt.set_ylabel("Pressure (bar gauge)")
    ax_pt.set_xlabel("Elapsed time (s)")
    ax_pt.legend(loc="upper right", fontsize=9)
    ax_pt.grid(True, alpha=0.35)

    plt.tight_layout()
    return fig
