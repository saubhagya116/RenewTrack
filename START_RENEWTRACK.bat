@echo off
setlocal
cd /d "%~dp0"
title RenewTrack - Subscription Renewal Manager

echo.
echo  ==========================================
echo       RenewTrack - Starting application
echo  ==========================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating a private Python environment...
    py -m venv venv
    if errorlevel 1 (
        echo.
        echo Could not create the environment. Check that Python is installed.
        echo You can download Python from https://www.python.org/downloads/windows/
        pause
        exit /b 1
    )
)

echo [2/3] Installing/checking required packages...
"venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo Package installation failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo [3/3] Starting RenewTrack...
echo.
echo On this laptop, open: http://127.0.0.1:5000
echo To use your phone, connect it to the SAME Wi-Fi and open:
echo http://YOUR-LAPTOP-IP:5000
echo.
echo Keep this window open while using the app.
echo Press Ctrl+C to stop RenewTrack.
echo.
"venv\Scripts\python.exe" app.py
pause
