#!/bin/bash
# ============================================================
# License Server 部署脚本
# 部署到 VPS: 149.104.12.203
# ============================================================

set -e

VPS_HOST="149.104.12.203"
VPS_USER="root"
VPS_PORT=22
REMOTE_DIR="/opt/license-server"

echo "========================================"
echo "Deploying License Server to VPS"
echo "========================================"
echo "Host: $VPS_HOST"
echo "Dir: $REMOTE_DIR"

# 构建 Docker 镜像
echo ""
echo "[1/5] Building Docker image..."
docker build -t license-server:latest -f license_server/Dockerfile .
docker tag license-server:latest license-server:2.0.0

# 导出镜像
echo ""
echo "[2/5] Exporting image..."
docker save license-server:latest | gzip > license_server.tar.gz

# 传输到 VPS
echo ""
echo "[3/5] Transferring to VPS..."
scp -P $VPS_PORT license_server.tar.gz $VPS_USER@$VPS_HOST:/tmp/

# SSH 到 VPS 执行部署
echo ""
echo "[4/5] Deploying on VPS..."
ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << 'ENDSSH'
    set -e

    echo "  Stopping existing container..."
    docker stop license-server || true
    docker rm license-server || true

    echo "  Loading Docker image..."
    docker load < /tmp/license_server.tar.gz

    echo "  Creating data directory..."
    mkdir -p /opt/license-server/data

    echo "  Starting container..."
    docker run -d \
        --name license-server \
        --restart always \
        -p 8443:8443 \
        -v /opt/license-server/data:/app/license_data \
        -e LICENSE_DB_PATH=/app/license_data/licenses.db \
        license-server:latest

    echo "  Cleaning up..."
    rm /tmp/license_server.tar.gz

    echo "  Health check..."
    sleep 5
    curl -f http://localhost:8443/health || echo "Warning: Health check failed"

    echo "  Done!"
ENDSSH

# 清理本地文件
echo ""
echo "[5/5] Cleanup..."
rm license_server.tar.gz

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo "License Server URL: https://$VPS_HOST:8443"
echo ""
echo "Test with:"
echo "  curl -X POST https://$VPS_HOST:8443/api/license/verify \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"license_key\":\"pro_test_001\",\"session_token\":\"test\",\"challenge_response\":\"test\",\"timestamp\":0}'"