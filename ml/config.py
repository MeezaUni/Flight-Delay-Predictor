"""Shared paths and feature definitions."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"

DATA_PATH = DATA_DIR / "Airlines.csv"
MODEL_PATH = MODELS_DIR / "flight_model.joblib"
METRICS_PATH = MODELS_DIR / "metrics.json"

CATEGORICAL_FEATURES = ["Airline", "AirportFrom", "AirportTo"]
NUMERIC_FEATURES = ["Flight", "DayOfWeek", "Time", "Length"]
FEATURES = ["Airline", "Flight", "AirportFrom", "AirportTo", "DayOfWeek", "Time", "Length"]
TARGET = "Delay"

RANDOM_STATE = 42
TEST_SIZE = 0.2

# Carrier codes that appear in the dataset (US domestic flights).
AIRLINE_NAMES = {
    "9E": "Endeavor Air",
    "AA": "American Airlines",
    "AS": "Alaska Airlines",
    "B6": "JetBlue",
    "CO": "Continental Airlines",
    "DL": "Delta Air Lines",
    "EV": "ExpressJet",
    "F9": "Frontier Airlines",
    "FL": "AirTran Airways",
    "HA": "Hawaiian Airlines",
    "MQ": "American Eagle (Envoy)",
    "OH": "PSA Airlines (Comair)",
    "OO": "SkyWest Airlines",
    "UA": "United Airlines",
    "US": "US Airways",
    "WN": "Southwest Airlines",
    "XE": "ExpressJet (XE)",
    "YV": "Mesa Airlines",
}

DAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}
