@echo off
rem One-click start on Windows: gets the data, trains the model if needed, and starts the app.
cd /d "%~dp0"

if not exist "data\Airlines.csv" (
    echo Downloading dataset...
    python scripts\download_data.py || goto :error
)

if not exist "models\flight_model.joblib" (
    echo Training model...
    python -m ml.train || goto :error
)

echo Starting Flight Delay Predictor at http://127.0.0.1:8000
start "" http://127.0.0.1:8000
python -m uvicorn backend.main:app --port 8000
goto :eof

:error
echo Something failed. Check the message above.
pause
