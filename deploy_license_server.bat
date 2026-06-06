@echo off
REM ============================================================
REM License Server 部署脚本 (Windows)
REM 部署到 VPS: 149.104.12.203
REM ============================================================

setlocal enabledelayedexpansion

set VPS_HOST=149.104.12.203
set VPS_USER=root
set VPS_PORT=22
set REMOTE_DIR=/opt/license-server

echo ========================================
echo Deploying License Server to VPS
echo ========================================
echo Host: %VPS_HOST%
echo Dir: %REMOTE_DIR%

REM 构建 Docker 镜像
echo.
echo [1/5] Building Docker image...
docker build -t license-server:latest -f license_server\Dockerfile .
docker tag license-server:latest license-server:2.0.0

REM 导出镜像
echo.
echo [2/5] Exporting image...
docker save license-server:latest > license_server.tar

REM 传输到 VPS
echo.
echo [3/5] Transferring to VPS...
scp -P %VPS_PORT% license_server.tar %VPS_USER%@%VPS_HOST%:/tmp/

REM SSH 到 VPS 执行部署
echo.
echo [4/5] Deploying on VPS...
ssh -p %VPS_PORT% %VPS_USER%@%VPS_HOST% (
    echo   Stopping existing container...
    docker stop license-server 2^>nul ^|^| true
    docker rm license-server 2^>nul ^|^| true

    echo   Loading Docker image...
    docker load ^< /tmp/license_server.tar

    echo   Creating data directory...
    mkdir C:\opt\license-server\data 2^>nul ^|^| true

    echo   Starting container...
    docker run -d --name license-server --restart always -p 8443:8443 license-server:latest

    echo   Cleaning up...
    del /tmp/license_server.tar

    echo   Done!
)

REM 清理本地文件
echo.
echo [5/5] Cleanup...
del license_server.tar

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo License Server URL: https://%VPS_HOST%:8443

pause