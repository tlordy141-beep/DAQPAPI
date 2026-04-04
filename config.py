"""
config.py — edit this file to configure a logging run.

This is the ONLY file you need to edit for a typical run.
All scripts in examples/ import from here.
"""

# ---------------------------------------------------------------------------
# Channel selection
# ---------------------------------------------------------------------------
# List the sensor names you want active for this run.
# Only listed channels are read from hardware — inactive channels are ignored
# entirely (no read calls, no CSV columns, no plot lines).
#
# Valid names:
#   Thermocouples  : "TC1", "TC2", "TC3"
#   Pressure trans.: "PT1", "PT2", "PT3", "PT4"
#
# "CJC" is not listed here — it is always read automatically whenever at
# least one TC channel is active (required for cold-junction compensation).
# CJC is also always included in the CSV output.
#
# Example — log only TC1 and PT1:
#   ACTIVE_CHANNELS = ["TC1", "PT1"]
ACTIVE_CHANNELS: list[str] = ["TC1", "PT1"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Sampling interval in seconds (e.g. 1.0 = one sample per second).
SAMPLE_INTERVAL_S: float = 1.0

# Output CSV file path.
# Set to None to auto-generate a timestamped file in the data/ folder,
# e.g. data/20260404_120000.csv
OUTPUT_PATH: str | None = None

# ---------------------------------------------------------------------------
# Real-time plot
# ---------------------------------------------------------------------------
# Set to True to show a live matplotlib plot while logging.
# Closing the plot window will NOT stop logging — it continues until Ctrl+C.
LIVE_PLOT: bool = True
