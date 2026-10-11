"""Request and response models for the API."""
from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    airline: str = Field(..., min_length=2, max_length=3, examples=["DL"])
    flight: int = Field(..., ge=1, le=9999, examples=[1234])
    origin: str = Field(..., min_length=3, max_length=3, examples=["ATL"])
    destination: str = Field(..., min_length=3, max_length=3, examples=["JFK"])
    day_of_week: int = Field(..., ge=1, le=7, description="1 = Monday, 7 = Sunday")
    departure_minutes: int = Field(..., ge=0, le=1439, description="Minutes after midnight")
    length_minutes: int = Field(..., ge=1, le=1000, description="Scheduled flight length in minutes")

    @field_validator("airline", "origin", "destination")
    @classmethod
    def upper(cls, value: str) -> str:
        return value.strip().upper()


class PredictResponse(BaseModel):
    delayed: bool
    status: str
    delay_probability: float
    confidence: float
    route_known: bool


class Airline(BaseModel):
    code: str
    name: str


class Day(BaseModel):
    value: int
    name: str


class OptionsResponse(BaseModel):
    airlines: list[Airline]
    airports: list[str]
    days: list[Day]


class RouteResponse(BaseModel):
    origin: str
    destination: str
    known: bool
    median_length: int | None = None
    flights: int = 0
