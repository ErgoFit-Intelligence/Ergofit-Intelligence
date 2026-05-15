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
cd /d "C:\Users\kriti\Documents\ergonomic-app"
python -m streamlit run app.py
echo.
echo  App stopped.
pause >nul
