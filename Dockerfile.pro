# ============================================================
# AI Privacy Gateway - Pro 版 Dockerfile
# 多阶段构建：Rust + PyArmor + Cython + Nuitka
# ============================================================
FROM python:3.11-slim AS rust-builder

WORKDIR /build

# 安装 Rust 编译工具链
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable && \
    . $HOME/.cargo/env && \
    cargo install maturin

# 复制 Rust 源码
COPY rust_src/integrity_check /build/integrity_check

# 编译 Rust 模块
WORKDIR /build/integrity_check
RUN . $HOME/.cargo/env && \
    maturin develop --release --out /build/wheels

# ============================================================
FROM python:3.11-slim AS pyarmor-builder

WORKDIR /build

# 安装 PyArmor
RUN pip install pyarmor==3.9.9

# 复制源码
COPY config.py mask_engine.py stream_buffer.py gateway_core.py database.py \
     license_client.py decay_manager.py main.py ./

# PyArmor 混淆
RUN mkdir -p obfuscated && \
    pyarmor gen --enable-rft --enable-bcc --enable-jit \
        --output obfuscated . || true

# ============================================================
FROM python:3.11-slim AS cython-builder

WORKDIR /build

# 安装 Cython
RUN pip install cython==3.0.10

# 复制混淆后的源码
COPY --from=pyarmor-builder /build/obfuscated /build/source

# 编译 Cython
RUN pip install numpy && \
    python -c "from Cython.Build import cythonize; import subprocess; \
    subprocess.run(['cythonize', '-3', 'config.py', 'mask_engine.py', 'stream_buffer.py', \
    'gateway_core.py', 'database.py', 'license_client.py', 'decay_manager.py', 'main.py'])"

# ============================================================
FROM python:3.11-slim AS nuitka-builder

WORKDIR /build

# 安装 Nuitka 和编译器
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    && rm -rf /var/lib/apt/lists/*

RUN pip install nuitka==2.4.8

# 复制 Cython 编译产物
COPY --from=cython-builder /build/*.c /build/
COPY --from=cython-builder /build/*.so /build/

# 复制 Rust wheel
COPY --from=rust-builder /build/wheels/*.whl /build/
RUN pip install *.whl

# ============================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn[standard]==0.30.0 \
    httpx==0.27.0 \
    sse-starlette==2.0.0

# 复制构建产物
COPY --from=nuitka-builder /build/*.so ./
COPY --from=nuitka-builder /build/main.py ./
COPY --from=nuitka-builder /build/config.py ./

# 复制静态文件
COPY --from=pyarmor-builder /build/obfuscated/static ./static || \
    mkdir -p static && echo "Static dir ready"

# 创建数据目录
RUN mkdir -p /app/vault_data

# 暴露端口
EXPOSE 9999

# 启动命令
CMD ["python", "-c", "from main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=9999)"]