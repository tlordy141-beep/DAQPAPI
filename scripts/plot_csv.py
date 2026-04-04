"""
plot_csv.py — plot a CSV log file produced by log_and_plot.py.

Plot appearance is controlled by config_run.py (PLOT_FIGSIZE, PLOT_COLORS,
PLOT_LINE_WIDTH), so the post-run plot matches the live plot style.

Run from the project root with the venv active:
    python scripts/plot_csv.py                            # pick from list
    python scripts/plot_csv.py data/20260404_120000.csv   # specific file
"""
import sys
import os
import glob

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import config_run
from analysis.plotting import load_csv, plot_all
import matplotlib.pyplot as plt

_DATA_DIR = os.path.join(_ROOT, "data")


def _pick_file() -> str:
    """List available CSV files in data/ and prompt the user to choose."""
    csvs = sorted(glob.glob(os.path.join(_DATA_DIR, "*.csv")))
    if not csvs:
        print(f"No CSV files found in {_DATA_DIR}")
        sys.exit(1)
    print("Available log files:")
    for i, path in enumerate(csvs):
        print(f"  [{i}] {os.path.basename(path)}")
    choice = input("Select index [0]: ").strip() or "0"
    return csvs[int(choice)]


def main():
    filepath = sys.argv[1] if len(sys.argv) >= 2 else _pick_file()

    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    data     = load_csv(filepath)
    n        = len(data["elapsed_s"])
    duration = data["elapsed_s"][-1] if n > 0 else 0.0
    print(f"Loaded {n} samples over {duration:.1f} s  \u2014  {os.path.basename(filepath)}")

    plot_all(
        data,
        title=os.path.basename(filepath),
        figsize=config_run.PLOT_FIGSIZE,
        colors=config_run.PLOT_COLORS,
        line_width=config_run.PLOT_LINE_WIDTH,
    )
    plt.show()


if __name__ == "__main__":
    main()
