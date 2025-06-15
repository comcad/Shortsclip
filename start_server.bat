@echo off
ECHO --- Starting Video Agent Server ---
ECHO.
ECHO This script will now launch the Python application.
ECHO Please keep this window open. Closing it will stop the server.
ECHO.

REM This command finds the correct python3 executable and uses it to run the app.
python3 app.py

pause
