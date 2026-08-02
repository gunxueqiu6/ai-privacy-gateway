@echo off
chcp 65001 >nul 2>&1
title AI Privacy Gateway
cd /d "%~dp0"

:: ── Banner ──────────────────────────────────────────────────
echo ============================================================
echo   AI Privacy Gateway v2.0.0
echo ============================================================
echo.

:: ── Find Python ─────────────────────────────────────────────
set "PYTHON_CMD="

:: 1) Try venv first
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    echo [OK] Using virtual environment
    goto :check_deps
)

:: 2) Try system python
where python >nul 2>&1 && set "PYTHON_CMD=python" && goto :check_deps
where python3 >nul 2>&1 && set "PYTHON_CMD=python3" && goto :check_deps
where py >nul 2>&1 && set "PYTHON_CMD=py" && goto :check_deps

echo [ERROR] Python not found. Install Python 3.8+ first:
echo   https://www.python.org/downloads/
pause
exit /b 1

:check_deps
:: ── Check dependencies ──────────────────────────────────────
echo [1/3] Checking dependencies...
%PYTHON_CMD% -c "import fastapi, uvicorn, httpx" 2>nul
if errorlevel 1 (
    echo [WARN] Dependencies missing, installing...
    %PYTHON_CMD% -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)
echo [OK] Dependencies ready
echo.

:: ── Check .env ──────────────────────────────────────────────
echo [2/3] Checking configuration...
if not exist ".env" (
    echo [WARN] .env not found, generating from .env.example...
    if exist ".env.example" (
        copy /y .env.example .env >nul
        %PYTHON_CMD% -c "import secrets; f=open('.env','a',encoding='utf-8'); f.write(f'ADMIN_PASSWORD={secrets.token_urlsafe(12)}\nJWT_SECRET={secrets.token_hex(32)}\n'); f.close()"
    ) else (
        %PYTHON_CMD% -c "import secrets; f=open('.env','w',encoding='utf-8'); f.write(f'TARGET_LLM=https://api.openai.com\nLISTEN_PORT=9999\nADMIN_PASSWORD={secrets.token_urlsafe(12)}\nJWT_SECRET={secrets.token_hex(32)}\nDB_TYPE=sqlite\nDB_PATH=./vault_data/privacy_vault.db\nMASK_ENGINE_TYPE=regex\n'); f.close()"
    )
    echo [OK] Configuration generated
) else (
    echo [OK] Configuration found
)
echo.

:: ── Start ───────────────────────────────────────────────────
echo [3/3] Starting gateway...
echo.
echo ============================================================
echo   Starting...
echo ============================================================
echo   Admin panel:  http://localhost:9999/admin
echo   API endpoint: http://localhost:9999/v1
echo   Press Ctrl+C to stop
echo ============================================================
echo.

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set LOG_FORMAT=text
set LOG_LEVEL=INFO

%PYTHON_CMD% main.py

pause
