@echo off
rem Double-click to start the server and open the v2 pages at http://127.0.0.1:8000/web/ (README, section v2).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv\Scripts\python.exe not found. Create the virtual environment and install requirements.txt first ^(README^).
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m src.api.launch
if errorlevel 1 pause
