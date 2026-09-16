@echo off
title Clean Logo Transparency
cls
echo.
echo  ============================================
echo   Cleaning logo.png transparency ...
echo  ============================================
echo.

cd /d "C:\Users\kriti\Desktop\Claude\Claude Projects\Ergonomic App"

REM Make sure Pillow is installed
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo  Installing Pillow (image library) ...
    python -m pip install --quiet Pillow
    echo.
)

python clean_logo.py

echo.
echo  ============================================
echo   Done. You can delete this .bat when finished.
echo  ============================================
echo.
pause
