@echo off
title ErgoFit Intelligence
cls
echo.
echo  ============================================
echo     ErgoFit Intelligence
echo     Ergonomic Assessment Tool
echo  ============================================
echo.
echo  Starting up... the browser will open automatically.
echo.
echo  To close the app: just close this window.
echo.
cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python from https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

REM Check streamlit, install if missing
python -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo  Streamlit not found. Installing dependencies...
    echo.
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    echo.
)

REM Run the app
python -m streamlit run app.py

echo.
echo  ============================================
echo  App stopped. Read any error message above.
echo  ============================================
echo.
pause
