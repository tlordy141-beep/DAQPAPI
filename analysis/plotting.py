"""
plotting.py — post-run and real-time matplotlib plotting.

Public API
----------
load_csv(filepath)
    Load a log CSV into a dict of numpy arrays.
    Empty cells (disconnected sensors) become NaN.

plot_all(data, title, figsize, colors, line_width)
    Two-subplot figure from a loaded CSV dict or a file path.
    TC temperatures on top, PT pressures on bottom.
    Creates only the subplots that have data (handles filtered runs).

LivePlot(sensor_names, figsize, colors, line_width)
    Real-time updating plot for use during logging.
    Call update() after each sample; close the window to stop plotting
    without stopping the logging loop.
"""
import csv
import itertools
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_csv(filepath: str) -> dict:
    """
    Load a log CSV file produced by scripts/log_and_plot.py.

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

    for i, name in enumerate(header[2:], start=2):
        values = []
        for row in rows:
            cell = row[i] if i < len(row) else ""
            values.append(float(cell) if cell else float("nan"))
        data[name] = np.array(values)

    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assign_colors(names: list[str], colors: dict) -> dict[str, str]:
    """
    Assign a matplotlib colour to each name.

    Uses the explicit colour from `colors` if provided; otherwise takes the
    next colour from the default matplotlib prop_cycle.
    """
    cycle = itertools.cycle(mpl.rcParams["axes.prop_cycle"].by_key()["color"])
    return {name: colors.get(name) or next(cycle) for name in names}


def _make_subplots(has_tc: bool, has_pt: bool, figsize: tuple):
    """
    Create 1 or 2 subplots depending on which sensor types are present.

    Returns (fig, ax_tc, ax_pt) where ax_tc or ax_pt may be None.
    """
    n = has_tc + has_pt
    if n == 2:
        fig, (ax_tc, ax_pt) = plt.subplots(2, 1, figsize=figsize, sharex=True)
        fig.subplots_adjust(hspace=0.08)
        return fig, ax_tc, ax_pt
    if has_tc:
        fig, ax_tc = plt.subplots(1, 1, figsize=figsize)
        return fig, ax_tc, None
    fig, ax_pt = plt.subplots(1, 1, figsize=figsize)
    return fig, None, ax_pt


def _style_tc_axes(ax, line_width: float, colors: dict, elapsed, data: dict,
                   tc_names: list[str]) -> None:
    """Draw TC lines + CJC reference onto ax_tc for a post-run plot."""
    for name in tc_names:
        ax.plot(elapsed, data[name], label=name,
                linewidth=line_width, color=colors[name])
    if "CJC" in data:
        ax.plot(elapsed, data["CJC"], label="CJC (ambient)",
                linewidth=1.0, linestyle="--", color=colors.get("CJC", "grey"), alpha=0.7)
    ax.set_ylabel("Temperature (\u00b0C)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.35)


def _style_pt_axes(ax, line_width: float, colors: dict, elapsed, data: dict,
                   pt_names: list[str]) -> None:
    """Draw PT lines + 0-bar reference onto ax_pt for a post-run plot."""
    for name in pt_names:
        ax.plot(elapsed, data[name], label=name,
                linewidth=line_width, color=colors[name])
    ax.axhline(0, color="black", linewidth=0.8, linestyle=":", label="0 bar")
    ax.set_ylabel("Pressure (bar gauge)")
    ax.set_xlabel("Elapsed time (s)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.35)


# ---------------------------------------------------------------------------
# Post-run plot
# ---------------------------------------------------------------------------

def plot_all(
    data,
    title: str = None,
    figsize: tuple[float, float] = (10, 7),
    colors: dict[str, str] = None,
    line_width: float = 1.4,
) -> plt.Figure:
    """
    Plot temperature and pressure channels from a logged CSV.

    Parameters
    ----------
    data : dict or str
        Either the dict returned by load_csv(), or a path to a CSV file.
        Passing a file path is a convenient shorthand.
    title : str, optional
        Figure title.  Defaults to the filename if data is a str.
    figsize : tuple[float, float]
        Figure size in inches (width, height).
    colors : dict[str, str], optional
        Map of sensor_name → matplotlib colour string.
        Channels not listed use the default colour cycle.
    line_width : float
        Line width for all sensor traces.

    Returns
    -------
    matplotlib.figure.Figure — call plt.show() afterwards to display.
    """
    colors = colors or {}

    if isinstance(data, str):
        title = title or os.path.basename(data)
        data  = load_csv(data)

    elapsed  = data["elapsed_s"]
    tc_names = [k for k in data if k.startswith("TC")]
    pt_names = [k for k in data if k.startswith("PT")]
    has_tc   = bool(tc_names)
    has_pt   = bool(pt_names)

    if not has_tc and not has_pt:
        raise ValueError("No TC or PT channels found in data.")

    # Assign colours to all lines that will be drawn
    all_names    = tc_names + (["CJC"] if "CJC" in data else []) + pt_names
    line_colors  = _assign_colors(all_names, colors)

    fig, ax_tc, ax_pt = _make_subplots(has_tc, has_pt, figsize)

    if title:
        fig.suptitle(title, fontsize=10, y=0.99)

    if ax_tc is not None:
        _style_tc_axes(ax_tc, line_width, line_colors, elapsed, data, tc_names)

    if ax_pt is not None:
        _style_pt_axes(ax_pt, line_width, line_colors, elapsed, data, pt_names)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Real-time plot
# ---------------------------------------------------------------------------

class LivePlot:
    """
    Real-time updating plot for use during a logging run.

    Usage
    -----
    live = LivePlot(sensor_names, figsize=..., colors=..., line_width=...)
    # inside logging loop:
    live.update(elapsed_s, physical_dict)
    # on exit:
    live.destroy()

    Sensor type is inferred from name prefix:
        "TC*" → temperature subplot
        "PT*" → pressure subplot
        "CJC" → dashed reference line on the temperature subplot

    If the user closes the window, is_open returns False and update() becomes
    a no-op — the logging loop continues uninterrupted.
    """

    def __init__(
        self,
        sensor_names: list[str],
        figsize: tuple[float, float] = (10, 6),
        colors: dict[str, str] = None,
        line_width: float = 1.4,
    ) -> None:
        """
        Parameters
        ----------
        sensor_names : list[str]
            Ordered list of all channels to plot (e.g. ["CJC", "TC1", "PT1"]).
            Typically the list returned by daq.reader.ordered_sensor_names().
        figsize : tuple[float, float]
            Figure size in inches.
        colors : dict[str, str], optional
            Per-channel colour overrides.  Unlisted channels use auto cycle.
        line_width : float
            Line width for sensor traces.
        """
        # matplotlib is imported here so that when LIVE_PLOT = False the
        # class is never instantiated and matplotlib is never imported at all.
        import matplotlib
        matplotlib.use("TkAgg")   # explicit backend for reliable Windows behaviour
        import matplotlib.pyplot as _plt
        self._plt = _plt

        colors = colors or {}

        self._tc_names  = [n for n in sensor_names if n.startswith("TC")]
        self._pt_names  = [n for n in sensor_names if n.startswith("PT")]
        self._has_tc    = bool(self._tc_names)
        self._has_pt    = bool(self._pt_names)
        self._lw        = line_width

        # Lines to draw: TC subplot gets TC channels + CJC reference
        tc_line_names  = self._tc_names + (["CJC"] if self._has_tc else [])
        all_line_names = tc_line_names + self._pt_names
        self._line_colors = _assign_colors(all_line_names, colors)

        self._lines:   dict[str, object] = {}
        self._data:    dict[str, list]   = {n: [] for n in all_line_names}
        self._elapsed: list[float]       = []
        self._fig   = None
        self._ax_tc = None
        self._ax_pt = None

        self._build(figsize)

    def _build(self, figsize: tuple) -> None:
        plt = self._plt
        plt.ion()

        self._fig, self._ax_tc, self._ax_pt = _make_subplots(
            self._has_tc, self._has_pt, figsize
        )
        if self._fig is None:
            return

        self._fig.suptitle(
            "Live DAQ readings  \u2014  close window to keep logging without plot",
            fontsize=10,
        )

        if self._ax_tc is not None:
            for name in self._tc_names:
                (line,) = self._ax_tc.plot(
                    [], [], label=name,
                    linewidth=self._lw, color=self._line_colors[name],
                )
                self._lines[name] = line
            if "CJC" in self._line_colors:
                (line,) = self._ax_tc.plot(
                    [], [], label="CJC (ambient)",
                    linewidth=1.0, linestyle="--",
                    color=self._line_colors["CJC"], alpha=0.7,
                )
                self._lines["CJC"] = line
            self._ax_tc.set_ylabel("Temperature (\u00b0C)")
            self._ax_tc.legend(loc="upper right", fontsize=9)
            self._ax_tc.grid(True, alpha=0.35)

        if self._ax_pt is not None:
            for name in self._pt_names:
                (line,) = self._ax_pt.plot(
                    [], [], label=name,
                    linewidth=self._lw, color=self._line_colors[name],
                )
                self._lines[name] = line
            self._ax_pt.axhline(0, color="black", linewidth=0.8,
                                linestyle=":", label="0 bar")
            self._ax_pt.set_ylabel("Pressure (bar gauge)")
            self._ax_pt.set_xlabel("Elapsed time (s)")
            self._ax_pt.legend(loc="upper right", fontsize=9)
            self._ax_pt.grid(True, alpha=0.35)

        plt.tight_layout()
        plt.pause(0.001)   # initial draw so the window appears before the first sample

    @property
    def is_open(self) -> bool:
        """True while the plot window is still open."""
        if self._fig is None:
            return False
        return self._plt.fignum_exists(self._fig.number)

    def update(self, elapsed_s: float, physical: dict) -> None:
        """
        Append one sample and redraw the plot.

        No-op if the window has been closed — logging continues unaffected.

        Parameters
        ----------
        elapsed_s : float
            Seconds since logging started.
        physical : dict[str, float | None]
            Physical values from read_all_physical().  None values → NaN gap.
        """
        if not self.is_open:
            return

        self._elapsed.append(elapsed_s)

        for name, line in self._lines.items():
            val = physical.get(name)
            self._data[name].append(float("nan") if val is None else val)
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
