@echo off
chcp 65001 >nul
echo ============================================================
echo   AI Privacy Gateway - Windows exe 构建脚本
echo ============================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

echo [1/4] 创建虚拟环境 .venv...
if not exist .venv (
    python -m venv .venv
) else (
    echo       .venv 已存在，跳过创建
)

echo [2/4] 安装依赖...
call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller -q

echo [3/4] 构建 exe ...
pyinstaller --noconfirm PrivacyGateway.spec

echo.
if exist "dist\PrivacyGateway.exe" (
    echo.
    echo ============================================================
    echo   构建成功！使用方法:
    echo.
    echo   1. 复制 .env.example 为 .env 并填入你的配置
    echo   2. 把 dist\PrivacyGateway.exe 和 .env 放在同一目录
    echo   3. 双击 PrivacyGateway.exe 启动服务
    echo   4. 浏览器打开 http://localhost:9999/admin
    echo ============================================================
) else (
    echo [错误] 构建失败，请查看上方错误信息
)

echo.
pause
