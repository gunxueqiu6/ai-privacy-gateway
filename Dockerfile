# ============================================================
# AI Privacy Gateway - Lite 版 Dockerfile
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY config.py mask_engine.py stream_buffer.py gateway_core.py database.py \
     license_client.py decay_manager.py main.py ./

# 复制静态文件
COPY static ./static

# ============================================================
# 运行时镜像
# ============================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制构建产物
COPY --from=builder /app/*.py ./
COPY --from=builder /app/static ./static

# 创建数据目录
RUN mkdir -p /app/vault_data

# 暴露端口
EXPOSE 9999

# 启动命令
CMD ["python", "main.py"]