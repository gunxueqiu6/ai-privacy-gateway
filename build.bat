@echo off
echo ================================
echo AI Privacy Gateway - Build Script
echo ================================
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
echo.

echo [2/3] Building executable...
pyinstaller --clean --noconfirm PrivacyGateway.spec
echo.

echo [3/3] Done!
echo.
echo Output: dist\PrivacyGateway.exe
echo.
pause