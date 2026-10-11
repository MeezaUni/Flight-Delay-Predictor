"""Download the airlines delay dataset into data/Airlines.csv.

The Kaggle dataset `jimschacko/airlines-dataset-to-predict-a-delay` is a copy of
the public OpenML "airlines" dataset (id 1169). This script fetches it from
OpenML so no Kaggle account is needed, and writes it with the same columns as
the Kaggle CSV.

Usage:
    python scripts/download_data.py
"""
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.config import DATA_DIR, DATA_PATH  # noqa: E402

OPENML_URL = "https://openml.org/data/v1/download/66526/airlines.arff"
COLUMNS = ["Airline", "Flight", "AirportFrom", "AirportTo", "DayOfWeek", "Time", "Length", "Delay"]


def parse_arff(text: str) -> pd.DataFrame:
    rows = []
    in_data = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        if not in_data:
            in_data = line.lower() == "@data"
            continue
        rows.append([value.strip().strip("'\"") for value in line.split(",")])
    return pd.DataFrame(rows, columns=COLUMNS)


def main() -> None:
    if DATA_PATH.exists():
        print(f"{DATA_PATH} already exists, nothing to do.")
        return

    print(f"Downloading {OPENML_URL} ...")
    with urllib.request.urlopen(OPENML_URL, timeout=120) as response:
        text = response.read().decode("utf-8")

    df = parse_arff(text)
    df.insert(0, "id", range(1, len(df) + 1))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    print(f"Saved {len(df):,} rows to {DATA_PATH}")


if __name__ == "__main__":
    main()
