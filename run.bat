@echo off
rem One-click start on Windows: gets the data, trains the model if needed, and starts the app.
cd /d "%~dp0"

rem Change this if 8642 is taken on your machine.
set PORT=8642

if not exist "data\Airlines.csv" (
    echo Downloading dataset...
    python scripts\download_data.py || goto :error
)

if not exist "models\flight_model.joblib" (
    echo Training model...
    python -m ml.train || goto :error
)

netstat -ano | findstr /R /C:"127.0.0.1:%PORT% .*LISTENING" /C:"0.0.0.0:%PORT% .*LISTENING" >nul
if not errorlevel 1 (
    echo Port %PORT% is already used by another program. Edit PORT at the top of run.bat and try again.
    goto :error
)

echo Starting Flight Delay Predictor at http://127.0.0.1:%PORT%
echo The browser opens once the model has loaded. Press Ctrl+C to stop.
start "" /b python scripts\open_browser.py %PORT%
python -m uvicorn backend.main:app --port %PORT%
goto :eof

:error
echo Something failed. Check the message above.
pause
