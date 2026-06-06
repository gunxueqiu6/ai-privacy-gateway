@echo off
echo ========================================
echo Building Rust Integrity Check Module
echo ========================================

cd /d "%~dp0"

REM 检查 Rust 环境
where cargo >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Rust...
    powershell -Command "Start-Process -FilePath 'https://win.rustup.rs' -Wait"
    call "%USERPROFILE%\.cargo\env"
)

REM 检查 maturin
pip show maturin >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing maturin...
    pip install maturin
)

REM 构建
echo Building with maturin...
maturin develop --release

echo.
echo ========================================
echo Build Complete!
echo ========================================
pause