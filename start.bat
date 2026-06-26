@echo off
chcp 65001 >nul
title AI Privacy Gateway

:: Switch to script directory
cd /d "%~dp0"

:: ── Colors ──────────────────────────────────────────────────
set "GREEN=[92m"
set "CYAN=[96m"
set "YELLOW=[93m"
set "RED=[91m"
set "BOLD=[1m"
set "RESET=[0m"

:: ── Banner ──────────────────────────────────────────────────
echo ============================================================
echo   AI Privacy Gateway
echo ============================================================
echo.

:: ── Step 1: Check if venv exists ────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo   [%YELLOW%WARN%RESET%] 未检测到虚拟环境 (.venv)
    echo.
    echo   请先运行 install.bat 完成安装:
    echo    双击 install.bat
    echo.
    echo   或手动创建:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: ── Step 2: Check Python ────────────────────────────────────
set "PYTHON_CMD="
where python >nul 2>nul && set "PYTHON_CMD=python" && goto :found
where python3 >nul 2>nul && set "PYTHON_CMD=python3" && goto :found
where py >nul 2>nul && set "PYTHON_CMD=py" && goto :found

echo   [%RED%ERROR%RESET%] 未检测到 Python，请先安装:
echo   https://www.python.org/downloads/
echo.
echo   安装时务必勾选 "Add Python to PATH"
pause
exit /b 1

:found

:: ── Step 3: Check if port 9999 is in use ──────────────────
echo   [1/3] 检查端口 9999...

netstat -ano | findstr ":9999 " >nul 2>nul
if errorlevel 1 (
    echo   [%GREEN%OK%RESET%] 端口 9999 可用
) else (
    echo   [%YELLOW%WARN%RESET%] 端口 9999 已被占用
    echo.
    echo   可能已经有 Privacy Gateway 在运行，或其它程序占用了端口。
    echo.
    echo   如需更换端口，编辑 .env 文件中的 LISTEN_PORT。
    echo.
    choice /c YN /m "是否继续尝试启动 "
    if errorlevel 2 exit /b 1
)
echo.

:: ── Step 4: Check .env exists ──────────────────────────────
echo   [2/3] 检查配置文件...
if exist ".env" (
    echo   [%GREEN%OK%RESET%] .env 配置文件已找到
) else (
    echo   [%YELLOW%WARN%RESET%] .env 文件不存在
    echo.
    echo   正在从 .env.example 生成最小配置...
    if exist ".env.example" (
        copy .env.example .env >nul
        python -c "import secrets; pw=secrets.token_urlsafe(12); f=open('.env','a'); f.write(f'ADMIN_PASSWORD={pw}\nJWT_SECRET={secrets.token_hex(32)}\n'); print(f'  生成的管理员密码: {pw}')"
        echo.
        echo   配置已生成，可以继续启动。
    ) else (
        echo.
        echo   请先运行 install.bat 完成配置。
        pause
        exit /b 1
    )
)
echo.

:: ── Step 5: Start Gateway ───────────────────────────────────
echo   [3/3] 启动网关...
echo.
echo ============================================================
echo   %GREEN%正在启动...%RESET%
echo ============================================================
echo.
echo   管理后台: http://localhost:9999
echo   健康检查: http://localhost:9999/health
echo.
echo   按 Ctrl+C 停止服务
echo.
echo ============================================================
echo.

set PYTHONIOENCODING=utf-8

:: Activate venv and start
call .venv\Scripts\activate.bat
python main.py

:: If start.py wrapper is preferred, uncomment the line below and comment the one above:
:: python start.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [%RED%ERROR%RESET%] 网关已停止
    echo.
    echo   可能的原因：
    echo     1. 端口 9999 已被占用 — 修改 .env 中的 LISTEN_PORT
    echo     2. Python 依赖未安装 — 运行 install.bat
    echo     3. .env 配置有误 — 检查 .env 文件
    echo.
    echo   如需帮助，请查看: https://github.com/gunxueqiu6/ai-privacy-gateway
)

pause
