@echo off
echo Starting YouTube Monitor with PubSubHubbub...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if ngrok is installed
ngrok version >nul 2>&1
if errorlevel 1 (
    echo Warning: ngrok is not installed. Install from https://ngrok.com/
    echo The system will work without ngrok but won't receive webhooks from YouTube.
    echo.
    pause
)

REM Install/upgrade required packages
echo Installing/upgrading required packages...
pip install -r requirements.txt

echo.
echo Starting PubSubHubbub monitoring...
echo.

REM Start the PubSubHubbub monitor
python youtube_monitor_pubsub.py --ngrok

pause
