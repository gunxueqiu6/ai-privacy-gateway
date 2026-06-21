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

echo [1/5] 创建虚拟环境 .venv...
if not exist .venv (
    python -m venv .venv
) else (
    echo       .venv 已存在，跳过创建
)

echo [2/5] 安装依赖...
call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller -q

echo [3/5] 构建 exe ...
pyinstaller --noconfirm PrivacyGateway.spec

echo.
if exist "dist\PrivacyGateway.exe" (
    echo [4/5] 生成安装程序图标 ...
    python installer\generate_icon.py

    echo [5/5] 构建 Windows 安装程序 ...
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
        echo.
        echo ============================================================
        echo   全部构建成功！
        echo.
        echo   EXE:       dist\PrivacyGateway.exe
        echo   安装程序: installer\Output\AI-Privacy-Gateway-Setup-1.1.0.exe
        echo.
        echo   双击安装程序即可安装到 Program Files。
        echo   或在 dist\ 中直接运行 PrivacyGateway.exe（需同级放 .env）
        echo ============================================================
    ) else (
        echo.
        echo ============================================================
        echo   EXE 构建成功，但未检测到 Inno Setup 6 编译器。
        echo.
        echo   安装程序脚本已就绪: installer\setup.iss
        echo   下载 Inno Setup 6: https://jrsoftware.org/isinfo.php
        echo.
        echo   EXE 文件: dist\PrivacyGateway.exe
        echo   使用方式: 把 .env.example 改为 .env 放同目录，双击 exe
        echo ============================================================
    )
) else (
    echo [错误] 构建失败，请查看上方错误信息
)

echo.
pause
