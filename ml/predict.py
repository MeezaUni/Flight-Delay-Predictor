"""Load the trained model and make predictions."""
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from ml.config import FEATURES, MODEL_PATH


class UnknownValueError(ValueError):
    """Raised when an airline or airport was never seen during training."""


@dataclass
class FlightInput:
    airline: str
    flight: int
    origin: str
    destination: str
    day_of_week: int
    departure_minutes: int
    length_minutes: int


class Predictor:
    def __init__(self, model_path: Path = MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"No trained model at {model_path}. Run `python -m ml.train` first."
            )
        # joblib unpickles, so only load model files produced locally by ml.train.
        bundle = joblib.load(model_path)
        self.pipeline = bundle["pipeline"]
        self.airlines: list[str] = bundle["airlines"]
        self.airports: list[str] = bundle["airports"]
        self.routes: dict[str, dict[str, int]] = bundle["routes"]
        self.metrics: dict = bundle["metrics"]
        self._airline_set = set(self.airlines)
        self._airport_set = set(self.airports)

    def route(self, origin: str, destination: str) -> dict[str, int] | None:
        return self.routes.get(f"{origin}-{destination}")

    def predict(self, flight: FlightInput) -> dict:
        if flight.airline not in self._airline_set:
            raise UnknownValueError(f"Unknown airline code '{flight.airline}'.")
        for code in (flight.origin, flight.destination):
            if code not in self._airport_set:
                raise UnknownValueError(f"Unknown airport code '{code}'.")

        row = pd.DataFrame(
            [[
                flight.airline,
                flight.flight,
                flight.origin,
                flight.destination,
                flight.day_of_week,
                flight.departure_minutes,
                flight.length_minutes,
            ]],
            columns=FEATURES,
        )
        delay_probability = float(self.pipeline.predict_proba(row)[0, 1])
        delayed = delay_probability >= 0.5
        return {
            "delayed": delayed,
            "status": "Delayed" if delayed else "On time",
            "delay_probability": round(delay_probability, 4),
            "confidence": round(delay_probability if delayed else 1 - delay_probability, 4),
            "route_known": self.route(flight.origin, flight.destination) is not None,
        }
