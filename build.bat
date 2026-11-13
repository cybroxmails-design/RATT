@echo off
echo ==========================================
echo   RATT Build Script
echo ==========================================
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo [2/3] Building the native helpers (needs MinGW-w64 gcc)...
python build_native.py
if errorlevel 1 (
    echo ERROR: Could not build assets\ratt_daemon.dll / assets\ratt_menu.dll
    pause
    exit /b 1
)
echo.

echo [3/3] Building RATT.exe with PyInstaller...
python -m PyInstaller RATT.spec --noconfirm --clean
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)
if defined RATT_SIGN_THUMBPRINT (
    signtool.exe sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /sha1 %RATT_SIGN_THUMBPRINT% dist\RATT.exe
)
echo.

echo Build complete: dist\RATT.exe
echo.
pause
