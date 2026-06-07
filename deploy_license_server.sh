#!/bin/bash

# License Server 部署脚本
# 部署到 VPS: 149.104.12.203

set -e

# 配置
VPS_IP="149.104.12.203"
VPS_USER="root"
DOCKER_IMAGE="ghcr.io/gunxueqiu6/license-server:latest"

echo "=========================================="
echo "AI Privacy Gateway License Server 部署"
echo "=========================================="

# 1. 构建 Docker 镜像
echo "[1/5] 构建 License Server Docker 镜像..."
docker build -t $DOCKER_IMAGE -f license_server/Dockerfile .

# 2. 推送镜像到 GHCR
echo "[2/5] 推送镜像到 GHCR..."
docker push $DOCKER_IMAGE

# 3. 上传配置文件到 VPS
echo "[3/5] 上传配置文件到 VPS..."
scp -o StrictHostKeyChecking=no nginx.conf $VPS_USER@$VPS_IP:/etc/nginx/sites-available/license-server.conf

# 4. 登录 VPS 并部署
echo "[4/5] 部署到 VPS..."
ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP << 'EOF'
    # 创建目录
    mkdir -p /opt/license-server
    mkdir -p /opt/license-server/license_data
    
    # 停止旧容器
    docker stop license-server || true
    docker rm license-server || true
    
    # 运行新容器
    docker run -d \
        --name license-server \
        -p 8443:8443 \
        -v /opt/license-server/license_data:/app/license_data \
        --restart always \
        ghcr.io/gunxueqiu6/license-server:latest
    
    # 配置 Nginx 反向代理
    ln -sf /etc/nginx/sites-available/license-server.conf /etc/nginx/sites-enabled/
    nginx -s reload
    
    echo "License Server 部署完成"
EOF

# 5. 验证部署
echo "[5/5] 验证部署..."
sleep 5
curl -f https://license.privacygw.com/health || echo "验证失败，请检查 VPS 状态"

echo "=========================================="
echo "部署完成！"
echo "License Server: https://license.privacygw.com"
echo "API: https://license.privacygw.com/api/license/activate"
echo "=========================================="