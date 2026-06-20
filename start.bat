@echo off
title AI Privacy Gateway

:: Switch to script directory
cd /d "%~dp0"

:: Find available Python
set PYTHON_CMD=
where python >nul 2>nul && set "PYTHON_CMD=python" && goto :found
where python3 >nul 2>nul && set "PYTHON_CMD=python3" && goto :found
where py >nul 2>nul && set "PYTHON_CMD=py" && goto :found

echo [ERROR] Python not found. Please install Python 3.8+:
echo         https://www.python.org/downloads/
echo.
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:found
echo ============================================
echo   AI Privacy Gateway - Setup + Launch
echo ============================================
echo.
echo Auto-configuring and starting...
echo.

set PYTHONIOENCODING=utf-8
"%PYTHON_CMD%" start.py --auto

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The gateway stopped. If you see errors above, please:
    echo   1. Check Python 3.8+ is installed
    echo   2. Run: pip install -r requirements.txt
    echo   3. Make sure port 9999 is not in use
)
pause
