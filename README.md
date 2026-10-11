# Flight Delay Predictor

A machine learning web app that predicts whether a US domestic flight will be delayed.
A Random Forest is trained on 539,383 flights. You enter a flight (airline, route, day,
departure time) and the app gives you the chance of a delay.

- **Model:** scikit-learn `RandomForestClassifier` (100 trees)
- **Backend:** FastAPI (REST API, auto docs at `/docs`)
- **Frontend:** HTML, CSS and JavaScript with no build step, served by the backend
- **Results on held-out test data:** 67.2% accuracy, 0.723 ROC AUC

## Quick start (Windows)

Double-click `run.bat`. It downloads the data, trains the model on the first run and
opens http://127.0.0.1:8642 (change `PORT` at the top of the file if that port is taken).

## Manual setup

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python scripts/download_data.py # writes data/Airlines.csv (about 20 MB)
python -m ml.train              # writes models/flight_model.joblib and models/metrics.json
uvicorn backend.main:app --reload --port 8642
```

Then open http://127.0.0.1:8642 for the app or http://127.0.0.1:8642/docs for the API.

To change the forest's settings:

```bash
python -m ml.train --n-estimators 200 --min-samples-leaf 5 --max-depth 30
```

Run the tests (the model must be trained first):

```bash
pytest
```

## Project structure

```
├── backend/
│   ├── main.py          FastAPI app: API routes, serves the frontend
│   └── schemas.py       Request/response validation (Pydantic)
├── frontend/
│   ├── index.html       Departure board, flight form, forecast, model performance
│   ├── styles.css
│   └── app.js
├── ml/
│   ├── config.py        Paths, feature lists, airline names
│   ├── data.py          Load and clean the dataset, route statistics
│   ├── train.py         Train, evaluate, save model and metrics
│   └── predict.py       Load the model and predict one flight
├── scripts/
│   ├── download_data.py Fetch the dataset (no Kaggle account needed)
│   └── open_browser.py  Opens the app once the server is ready (used by run.bat)
├── tests/
│   └── test_api.py
├── data/                Airlines.csv (not committed)
├── models/              Trained model (not committed) and metrics.json
├── notebooks/
│   └── mlminiprj_colab.py   Original Colab notebook
├── docs/                Report, presentation, paper summaries, reference papers
├── requirements.txt
└── run.bat
```

## Dataset

[Airlines Dataset to Predict a Delay](https://www.kaggle.com/datasets/jimschacko/airlines-dataset-to-predict-a-delay)
on Kaggle. It is the same data as the public [OpenML "airlines" dataset](https://www.openml.org/d/1169),
which is where `download_data.py` gets it. If you already have the Kaggle `Airlines.csv`, put it in `data/`.

| Column | Meaning |
|---|---|
| `Airline` | Carrier code, e.g. `DL` |
| `Flight` | Flight number |
| `AirportFrom`, `AirportTo` | Origin and destination airport codes |
| `DayOfWeek` | 1 = Monday … 7 = Sunday |
| `Time` | Scheduled departure, in minutes after midnight (18:30 = 1110) |
| `Length` | Scheduled flight length, in minutes |
| `Delay` | Target: 1 = delayed, 0 = on time |

44.5% of the flights are delayed, so the classes are fairly balanced.

## How it works

1. `ml/train.py` loads the CSV, drops missing rows and makes a stratified 80/20 train/test split.
2. A scikit-learn `Pipeline` ordinal-encodes the three categorical columns (unknown values become -1)
   and passes the numeric columns through to the Random Forest.
3. The model is scored on the test set (accuracy, ROC AUC, precision/recall, confusion matrix,
   feature importance) and saved together with the list of airlines, airports and typical
   flight lengths for each route.
4. The FastAPI backend loads that bundle once at startup. The frontend calls it to fill the
   dropdowns, look up the typical length of a route, and get predictions.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Server and model status |
| GET | `/api/options` | Airlines (code and name), airports, days of the week |
| GET | `/api/route?origin=ATL&destination=JFK` | Typical flight length and number of flights on a route |
| POST | `/api/predict` | Predict one flight |
| GET | `/api/metrics` | Test-set scores, confusion matrix, feature importance |

Example request:

```bash
curl -X POST http://127.0.0.1:8642/api/predict -H "Content-Type: application/json" \
  -d '{"airline":"DL","flight":1234,"origin":"ATL","destination":"JFK","day_of_week":3,"departure_minutes":1110,"length_minutes":145}'
```

```json
{"delayed": true, "status": "Delayed", "delay_probability": 0.6069, "confidence": 0.6069, "route_known": true}
```

## Limitations

The model only knows schedule information. It has no weather, air traffic or aircraft data,
which is why accuracy stays around two out of three. It is a learning project, not a tool
for real travel decisions.
