"""Load and clean the airlines dataset."""
from pathlib import Path

import pandas as pd

from ml.config import DATA_PATH, FEATURES, TARGET


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run `python scripts/download_data.py` "
            "or place the Kaggle Airlines.csv there."
        )

    df = pd.read_csv(path)
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")

    df = df[FEATURES + [TARGET]].dropna()
    for col in ("Airline", "AirportFrom", "AirportTo"):
        df[col] = df[col].astype(str).str.strip()
    for col in ("Flight", "DayOfWeek", "Time", "Length", TARGET):
        df[col] = df[col].astype(int)
    return df


def route_durations(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Typical flight length (minutes) and flight count for every origin-destination pair."""
    grouped = df.groupby(["AirportFrom", "AirportTo"])["Length"].agg(["median", "count"])
    return {
        f"{origin}-{dest}": {"median_length": int(row["median"]), "flights": int(row["count"])}
        for (origin, dest), row in grouped.iterrows()
    }
