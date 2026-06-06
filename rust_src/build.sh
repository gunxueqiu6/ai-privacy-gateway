#!/bin/bash
set -e

echo "========================================"
echo "Building Rust Integrity Check Module"
echo "========================================"

cd "$(dirname "$0")"

# 检查 Rust 环境
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# 检查 maturin
if ! command -v maturin &> /dev/null; then
    echo "Installing maturin..."
    pip install maturin
fi

# 构建
echo "Building with maturin..."
maturin develop --release

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo ""
echo "Python module: integrity_check"
echo "Test with: python -c 'from integrity_check import run_integrity_check; print(run_integrity_check())'"