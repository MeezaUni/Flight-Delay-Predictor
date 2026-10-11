"""FastAPI app: prediction API plus the static frontend.

Run with:
    uvicorn backend.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend.schemas import (
    Airline,
    Day,
    OptionsResponse,
    PredictRequest,
    PredictResponse,
    RouteResponse,
)
from ml.config import AIRLINE_NAMES, DAY_NAMES, ROOT_DIR
from ml.predict import FlightInput, Predictor, UnknownValueError

FRONTEND_DIR = ROOT_DIR / "frontend"
state: dict[str, Predictor] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["predictor"] = Predictor()
    yield
    state.clear()


app = FastAPI(
    title="Flight Delay Predictor",
    description="Random Forest model that predicts whether a US domestic flight will be delayed.",
    version="1.0.0",
    lifespan=lifespan,
)


def predictor() -> Predictor:
    return state["predictor"]


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": "predictor" in state}


@app.get("/api/options", response_model=OptionsResponse)
def options() -> OptionsResponse:
    p = predictor()
    return OptionsResponse(
        airlines=[Airline(code=c, name=AIRLINE_NAMES.get(c, c)) for c in p.airlines],
        airports=p.airports,
        days=[Day(value=v, name=n) for v, n in DAY_NAMES.items()],
    )


@app.get("/api/route", response_model=RouteResponse)
def route(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
) -> RouteResponse:
    origin, destination = origin.upper(), destination.upper()
    info = predictor().route(origin, destination)
    if info is None:
        return RouteResponse(origin=origin, destination=destination, known=False)
    return RouteResponse(origin=origin, destination=destination, known=True, **info)


@app.get("/api/metrics")
def metrics() -> dict:
    return predictor().metrics


@app.post("/api/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    if request.origin == request.destination:
        raise HTTPException(status_code=422, detail="Origin and destination must be different airports.")
    try:
        result = predictor().predict(FlightInput(**request.model_dump()))
    except UnknownValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PredictResponse(**result)


# Mounted last so /api routes take priority.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
