"""
config_run.py — run configuration for logging and plotting.

Edit this file before each test run.
Hardware channel definitions live in config_hardware.py.

This file is read by:
  scripts/read_once.py    — ACTIVE_CHANNELS
  scripts/log_and_plot.py — all parameters
  scripts/plot_csv.py     — plot appearance parameters
"""

# ---------------------------------------------------------------------------
# Channel selection
# ---------------------------------------------------------------------------
# List the sensor names to activate for this run.
# Names must match the sensor_name values defined in config_hardware.py.
# Only listed channels are read from hardware and saved to the CSV.
# CJC is always included automatically (required for TC compensation).
#
# Example — log only TC1 and both powered pressure sensors:
#   ACTIVE_CHANNELS = ["TC1", "PT3", "PT4"]
#
ACTIVE_CHANNELS: list[str] = ["TC1", "TC2", "TC3", "PT1", "PT2", "PT3", "PT4"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# How often to take a sample (seconds). 1.0 = one sample per second.
SAMPLE_INTERVAL_S: float = 1.0

# Output CSV file path.
# None = auto-generate a timestamped file in the data/ folder,
# e.g.  data/20260404_120000.csv
OUTPUT_PATH: str | None = None

# ---------------------------------------------------------------------------
# Live plot
# ---------------------------------------------------------------------------
# Show a real-time matplotlib window while logging.
# Closing the plot window will NOT stop logging — it continues until Ctrl+C.
LIVE_PLOT: bool = True

# ---------------------------------------------------------------------------
# Plot appearance
# (applies to both the live plot and the CSV post-run plot)
# ---------------------------------------------------------------------------
# Figure width and height in inches.
PLOT_FIGSIZE: tuple[float, float] = (12, 7)

# Line width for all sensor traces.
PLOT_LINE_WIDTH: float = 1.5

# Per-channel colours.
# Use any named matplotlib colour or hex string (e.g. "#1f77b4").
# Any channel not listed here uses matplotlib's default colour cycle.
# Reference: https://matplotlib.org/stable/gallery/color/named_colors.html
PLOT_COLORS: dict[str, str] = {
    "TC1": "firebrick",
    "TC2": "darkorange",
    "TC3": "goldenrod",
    "PT1": "royalblue",
    "PT2": "mediumseagreen",
    "PT3": "mediumpurple",
    "PT4": "saddlebrown",
    "CJC": "grey",
}
