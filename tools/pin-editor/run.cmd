@echo off
REM Start the Burton Pin Editor and open it in the browser.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run setup.cmd first.
  pause
  exit /b 1
)
echo Starting Burton Pin Editor at http://pins.local  (press Ctrl+C to stop)
start "" http://pins.local
".venv\Scripts\python.exe" app.py
