@echo off
chcp 65001 >nul
title AI Privacy Gateway — 一键安装

setlocal enabledelayedexpansion

:: ── Colors ──────────────────────────────────────────────────
set "GREEN=[92m"
set "CYAN=[96m"
set "YELLOW=[93m"
set "RED=[91m"
set "BOLD=[1m"
set "RESET=[0m"

:: ── Banner ──────────────────────────────────────────────────
echo ============================================================
echo   AI Privacy Gateway - 一键安装脚本
echo ============================================================
echo.
echo   本脚本将自动完成：
echo     1. 检查 Python 环境
echo     2. 创建虚拟环境
echo     3. 安装依赖
echo     4. 生成配置文件
echo     5. 创建桌面快捷方式
echo.
echo ============================================================
echo.

:: ── Step 1: Check Python ─────────────────────────────────────
echo [1/5] 检查 Python 环境...

:: Find Python
set "PYTHON_CMD="
for %%C in (python python3 py) do (
    where %%C >nul 2>nul && set "PYTHON_CMD=%%C" && goto :py_found
)
goto :py_not_found

:py_found
:: Check version >= 3.10
for /f "tokens=2 delims= " %%V in ('%PYTHON_CMD% --version 2^>nul') do set "PY_VERSION=%%V"
if not defined PY_VERSION (
    goto :py_not_found
)

:: Parse major.minor
for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

:: Remove potential trailing chars from minor
for /f "delims=.abcdefghijklmnopqrstuvwxyz- " %%n in ("!PY_MINOR!") do set "PY_MINOR=%%n"

if !PY_MAJOR! lss 3 (
    goto :py_version_bad
)
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 10 (
    goto :py_version_bad
)

echo   [OK] Python !PY_VERSION! 已安装
echo.
goto :step2

:py_not_found
echo   [%RED%FAIL%RESET%] 未检测到 Python
echo.
echo   请从 https://www.python.org/downloads/ 下载 Python 3.10+
echo.
echo   安装时务必勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:py_version_bad
echo   [%RED%FAIL%RESET%] 需要 Python 3.10+, 当前版本: !PY_VERSION!
echo.
echo   请从 https://www.python.org/downloads/ 下载最新 Python
echo.
pause
exit /b 1

:: ── Step 2: Create Virtual Environment ────────────────────────
:step2
echo [2/5] 创建虚拟环境...
if exist ".venv\Scripts\activate.bat" (
    echo   [%GREEN%SKIP%RESET%] .venv 已存在，跳过创建
) else (
    echo   正在创建 .venv...
    "%PYTHON_CMD%" -m venv .venv
    if errorlevel 1 (
        echo   [%RED%FAIL%RESET%] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo   [%GREEN%OK%RESET%] 虚拟环境已创建
)
echo.

:: ── Step 3: Install Dependencies ──────────────────────────────
echo [3/5] 安装依赖...

:: Upgrade pip first
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
if errorlevel 1 (
    echo   [%YELLOW%WARN%RESET%] pip 升级失败，继续安装
)

:: Install requirements
pip install -r requirements.txt -q
if errorlevel 1 (
    echo   [%RED%FAIL%RESET%] 依赖安装失败
    pause
    exit /b 1
)
echo   [%GREEN%OK%RESET%] 依赖安装完成
echo.

:: ── Step 4: Generate .env File ────────────────────────────────
echo [4/5] 生成配置文件...

if exist ".env" (
    echo   [%GREEN%SKIP%RESET%] .env 已存在，跳过创建
    echo.
    echo   如需重新配置，请删除 .env 文件后重新运行本脚本
) else (
    echo   正在从 .env.example 生成 .env ...
    if exist ".env.example" (
        copy .env.example .env >nul

        :: Generate random admin password
        python -c "import secrets; print(secrets.token_urlsafe(12))" > "%TEMP%\privacy_gw_pw.tmp"
        set /p ADMIN_PW=<"%TEMP%\privacy_gw_pw.tmp"
        del "%TEMP%\privacy_gw_pw.tmp"

        :: Replace placeholder with generated password
        python -c "
p = open('.env', encoding='utf-8').read()
p = p.replace('ADMIN_PASSWORD=', f'ADMIN_PASSWORD={%ADMIN_PW%}')
open('.env', 'w', encoding='utf-8').write(p)
"
        :: Generate JWT secret
        python -c "import secrets; f=open('.env','a',encoding='utf-8'); f.write(f'\n# 自动生成的 JWT 密钥\nJWT_SECRET={secrets.token_hex(32)}\n')"

        echo   [%GREEN%OK%RESET%] .env 文件已生成
        echo.
        echo   管理员密码: %CYAN%%ADMIN_PW%%RESET%
        echo   请牢记此密码，用于登录管理后台
        echo.
    ) else (
        echo   [%YELLOW%WARN%RESET%] 未找到 .env.example，创建最小配置...
        (
            echo # AI Privacy Gateway 配置文件
            echo TARGET_LLM=https://api.openai.com
            echo LISTEN_PORT=9999
            echo DB_PATH=./vault_data/privacy_vault.db
            echo DB_TYPE=sqlite
            echo MASK_ENGINE_TYPE=regex
            echo UPSTREAM_API_KEY=
        ) > .env

        :: Generate random admin password
        python -c "import secrets; pw=secrets.token_urlsafe(12); open('.env','a',encoding='utf-8').write(f'ADMIN_PASSWORD={pw}\n'); print(pw)" > "%TEMP%\privacy_gw_pw.tmp"
        set /p ADMIN_PW=<"%TEMP%\privacy_gw_pw.tmp"
        del "%TEMP%\privacy_gw_pw.tmp"

        python -c "import secrets; open('.env','a',encoding='utf-8').write(f'JWT_SECRET={secrets.token_hex(32)}\n')"

        echo   [%GREEN%OK%RESET%] 最小配置文件已生成
        echo.
        echo   管理员密码: %CYAN%%ADMIN_PW%%RESET%
    )
)
echo.

:: ── Step 5: Create Desktop Shortcut ──────────────────────────
echo [5/5] 创建桌面快捷方式...

:: Create a shortcut.vbs script
set "SHORTCUT_FILE=%USERPROFILE%\Desktop\AI Privacy Gateway.lnk"
set "SCRIPT_DIR=%CD%"

if exist "%SHORTCUT_FILE%" (
    echo   [%GREEN%SKIP%RESET%] 桌面快捷方式已存在
) else (
    :: Create VBS script for shortcut
    set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"
    (
        echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
        echo Set Shortcut = WshShell.CreateShortcut^("%SHORTCUT_FILE%"^)
        echo Shortcut.TargetPath = "%SCRIPT_DIR%\start.bat"
        echo Shortcut.WorkingDirectory = "%SCRIPT_DIR%"
        echo Shortcut.Description = "AI Privacy Gateway - 隐私代理网关"
        echo Shortcut.IconLocation = "%SCRIPT_DIR%\.venv\Scripts\python.exe, 0"
        echo Shortcut.Save
    ) > "%VBS_SCRIPT%"

    cscript //nologo "%VBS_SCRIPT%" >nul 2>nul
    del "%VBS_SCRIPT%" >nul 2>nul

    if exist "%SHORTCUT_FILE%" (
        echo   [%GREEN%OK%RESET%] 桌面快捷方式已创建
    ) else (
        echo   [%YELLOW%WARN%RESET%] 自动创建快捷方式失败
        echo   您可以手动创建 start.bat 的快捷方式到桌面
    )
)
echo.

:: ── Done ─────────────────────────────────────────────────────
echo ============================================================
echo   %GREEN%安装完成！%RESET%
echo ============================================================
echo.
echo   启动方式：
echo.
echo     方式1: 双击桌面 "AI Privacy Gateway" 快捷方式
echo     方式2: 双击 start.bat
echo     方式3: 运行 start.py (交互式配置向导)
echo.
echo   启动后打开浏览器访问:
echo     http://localhost:9999          — 管理后台
echo     http://localhost:9999/health   — 健康检查
echo.
echo   管理员密码: %CYAN%%ADMIN_PW%%RESET%
echo.
echo   如需修改配置，编辑 .env 文件后重启即可。
echo.
echo ============================================================
echo.

pause
