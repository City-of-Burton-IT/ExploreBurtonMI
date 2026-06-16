@echo off
REM One-time setup for the Burton Pin Editor (venv + deps + pins.local hosts entry).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
echo.
pause
