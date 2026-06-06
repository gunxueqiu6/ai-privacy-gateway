# ============================================================
# AI Privacy Gateway - Lite 版 Dockerfile
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 仅安装已编译的 wheel，避免 gcc 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary :all: \
    fastapi uvicorn httpx sse-starlette python-multipart \
    redis pytest pytest-asyncio \
    && rm -rf /root/.cache

# 复制源码
COPY *.py ./
COPY static ./static

RUN mkdir -p /app/vault_data

EXPOSE 9999

CMD ["python", "main.py"]
