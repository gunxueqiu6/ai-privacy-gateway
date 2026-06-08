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
COPY config.py mask_engine.py stream_buffer.py gateway_core.py database.py main.py ./

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

# 复制 Python 包和构建产物
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/*.py ./
COPY --from=builder /app/static ./static

# 创建数据目录
RUN mkdir -p /app/vault_data

# 暴露端口
EXPOSE 9999

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9999/health')" || exit 1

# 切换非 root 用户
USER appuser

# 启动命令
CMD ["python", "main.py"]