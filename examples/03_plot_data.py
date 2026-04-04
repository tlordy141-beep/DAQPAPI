"""
03_plot_data.py — plot a CSV log file produced by 02_log_data.py.

Usage:
    python examples/03_plot_data.py data/20260404_120000.csv   # specific file
    python examples/03_plot_data.py                            # pick from list
"""
import sys
import os
import glob

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from analysis.plotting import load_csv, plot_all
import matplotlib.pyplot as plt

_DATA_DIR = os.path.join(_ROOT, "data")


def _pick_file() -> str:
    """List available CSV files in data/ and let the user choose one."""
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
    if len(sys.argv) >= 2:
        filepath = sys.argv[1]
    else:
        filepath = _pick_file()

    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    data     = load_csv(filepath)
    n        = len(data["elapsed_s"])
    duration = data["elapsed_s"][-1] if n > 0 else 0.0
    print(f"Loaded {n} samples over {duration:.1f} s  \u2014  {os.path.basename(filepath)}")

    plot_all(data, title=os.path.basename(filepath))
    plt.show()


if __name__ == "__main__":
    main()
