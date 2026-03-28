@echo off
cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed.
    echo.
    echo Please install Python 3.10 or later:
    echo   1. Go to https://www.python.org/downloads/
    echo   2. Download and run the installer
    echo   3. IMPORTANT: Check "Add Python to PATH" during installation
    echo   4. Restart your computer, then run this script again
    echo.
    pause
    exit /b 1
)

:: Check if FFmpeg is installed (needed for Whisper fallback)
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: FFmpeg is not installed.
    echo Videos without subtitles will be skipped.
    echo To enable Whisper transcription, install FFmpeg:
    echo   https://www.gyan.dev/ffmpeg/builds/ (download "essentials" build)
    echo.
)

:: Create venv and install dependencies if needed
if not exist ".venv" (
    echo Setting up for first run...
    echo This may take a few minutes.
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python is installed correctly.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        echo Check your internet connection and try again.
        pause
        exit /b 1
    )
    echo.
    echo Setup complete!
    echo.
) else (
    call .venv\Scripts\activate.bat
)

:: Check if config.txt exists
if not exist "config.txt" (
    echo.
    echo ERROR: config.txt not found.
    echo.
    echo Please copy config.example.txt to config.txt and fill in your API keys:
    echo   copy config.example.txt config.txt
    echo   Then edit config.txt with your credentials.
    echo.
    pause
    exit /b 1
)

python summarizer.py
