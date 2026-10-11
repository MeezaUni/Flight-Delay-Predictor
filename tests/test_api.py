"""API tests. Require a trained model (python -m ml.train)."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from ml.config import MODEL_PATH

pytestmark = pytest.mark.skipif(not MODEL_PATH.exists(), reason="model not trained")

FLIGHT = {
    "airline": "DL",
    "flight": 1234,
    "origin": "ATL",
    "destination": "JFK",
    "day_of_week": 3,
    "departure_minutes": 1110,
    "length_minutes": 145,
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "model_loaded": True}


def test_options(client):
    body = client.get("/api/options").json()
    codes = {a["code"] for a in body["airlines"]}
    assert {"DL", "AA", "WN"} <= codes
    assert "ATL" in body["airports"]
    assert [d["value"] for d in body["days"]] == list(range(1, 8))


def test_route_known_and_unknown(client):
    known = client.get("/api/route", params={"origin": "atl", "destination": "jfk"}).json()
    assert known["known"] is True
    assert known["median_length"] > 0

    unknown = client.get("/api/route", params={"origin": "GUM", "destination": "BGR"}).json()
    assert unknown["known"] is False


def test_predict(client):
    response = client.post("/api/predict", json=FLIGHT)
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["delay_probability"] <= 1
    assert body["delayed"] == (body["delay_probability"] >= 0.5)
    assert body["status"] in {"Delayed", "On time"}
    assert body["confidence"] >= 0.5


def test_predict_lowercase_codes(client):
    response = client.post("/api/predict", json={**FLIGHT, "airline": "dl", "origin": "atl", "destination": "jfk"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "override, message",
    [
        ({"airline": "ZZ"}, "Unknown airline"),
        ({"origin": "XXX"}, "Unknown airport"),
        ({"destination": "ATL"}, "must be different"),
    ],
)
def test_predict_rejects_bad_input(client, override, message):
    response = client.post("/api/predict", json={**FLIGHT, **override})
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_predict_validates_ranges(client):
    assert client.post("/api/predict", json={**FLIGHT, "day_of_week": 8}).status_code == 422
    assert client.post("/api/predict", json={**FLIGHT, "departure_minutes": 1440}).status_code == 422


def test_metrics(client):
    body = client.get("/api/metrics").json()
    assert 0.5 < body["accuracy"] < 1
    assert len(body["confusion_matrix"]["matrix"]) == 2
    assert len(body["feature_importance"]) == 7


def test_frontend_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Flight Delay Predictor" in response.text
