@echo off
echo ==========================================
echo   RATT Build Script
echo ==========================================
echo.

echo [1/4] Installing dependencies...
pip install pyperclip pystray Pillow keyboard cryptography pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo [2/4] Generating application icon...
python generate_icon.py
if errorlevel 1 (
    echo WARNING: Could not generate icon, using default
)
echo.

echo [3/4] Building RATT.exe with PyInstaller...
pyinstaller --onefile --windowed --name=RATT --icon=assets/ratt_icon.ico --add-data "assets;assets" ratt/main.py
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)
echo.

echo [4/4] Build complete!
echo.
echo RATT.exe is located at: dist\RATT.exe
echo.
pause
