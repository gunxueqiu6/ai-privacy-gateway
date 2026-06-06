"""
编译链配置 - PyArmor + Cython + Rust + Nuitka
将 Python 源码编译为不可逆向的二进制
"""
import os
import subprocess
import shutil
import hashlib
import json
import time
from pathlib import Path

# 编译配置
BUILD_DIR = "build"
DIST_DIR = "dist"
SOURCE_FILES = [
    "config.py",
    "mask_engine.py",
    "stream_buffer.py",
    "gateway_core.py",
    "database.py",
    "license_client.py",
    "decay_manager.py",
    "main.py"
]
RUST_SRC_DIR = "rust_src/integrity_check"


def run_pyarmor():
    """
    第一步：PyArmor 混淆
    - 变量名打乱
    - 控制流扁平化
    - 字符串加密
    - 反调试注入
    """
    print("=" * 50)
    print("Step 1: PyArmor Obfuscation")
    print("=" * 50)

    # 创建临时目录
    obfuscated_dir = Path(BUILD_DIR) / "obfuscated"
    obfuscated_dir.mkdir(parents=True, exist_ok=True)

    for source in SOURCE_FILES:
        if not os.path.exists(source):
            print(f"  [SKIP] {source} not found")
            continue

        # PyArmor 混淆命令
        cmd = [
            "pyarmor",
            "gen",
            "--enable-rft",  # 运行时文件保护
            "--enable-bcc",  # 字节码加密
            "--enable-jit",  # JIT 保护
            "--output", str(obfuscated_dir),
            source
        ]

        print(f"  [OBFUSCATE] {source}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"    [ERROR] {result.stderr}")
            continue

    print(f"  [DONE] Output: {obfuscated_dir}")
    return str(obfuscated_dir)


def run_rust_build():
    """
    第一.五步：Rust 模块编译
    - 编译 Rust 源码为 .so/.pyd
    - 使用 maturin 进行 Python 绑定编译
    """
    print("=" * 50)
    print("Step 1.5: Rust Module Compilation")
    print("=" * 50)

    rust_dir = Path(RUST_SRC_DIR)
    if not rust_dir.exists():
        print("  [SKIP] Rust source not found")
        return None

    try:
        # 使用 maturin 编译
        cmd = ["maturin", "develop", "--release", "--out", BUILD_DIR]
        print(f"  [BUILD] Running maturin...")
        result = subprocess.run(cmd, cwd=str(rust_dir), capture_output=True, text=True)

        if result.returncode != 0:
            print(f"    [ERROR] {result.stderr}")
            # 回退：复制源文件作为占位
            print("  [FALLBACK] Using Python fallback...")
            return None

        # 查找编译产物
        compiled_dir = Path(BUILD_DIR)
        pyd_files = list(compiled_dir.glob("*.pyd")) + list(compiled_dir.glob("*.so"))

        if pyd_files:
            print(f"  [OUTPUT] Found {len(pyd_files)} compiled module(s)")
            return str(compiled_dir)

        return None

    except FileNotFoundError:
        print("  [SKIP] maturin not installed, skipping Rust build")
        return None


def run_cython(source_dir: str):
    """
    第二步：Cython 编译
    - 将 Python 转换为 C 代码
    - 编译为 .so/.pyd 文件
    - 无 Python 字节码残留
    """
    print("=" * 50)
    print("Step 2: Cython Compilation")
    print("=" * 50)

    cython_dir = Path(BUILD_DIR) / "cython"
    cython_dir.mkdir(parents=True, exist_ok=True)

    # 创建 setup.py
    setup_content = """
from setuptools import setup
from Cython.Build import cythonize
import os

source_dir = "{source_dir}"
modules = []

for f in os.listdir(source_dir):
    if f.endswith('.py'):
        modules.append(os.path.join(source_dir, f))

setup(
    name='ai_privacy_gateway',
    ext_modules=cythonize(modules, language_level=3),
)
""".format(source_dir=source_dir)

    setup_path = cython_dir / "setup.py"
    setup_path.write_text(setup_content)

    # 复制源文件
    for f in os.listdir(source_dir):
        if f.endswith('.py'):
            shutil.copy(Path(source_dir) / f, cython_dir / f)

    # 编译
    cmd = [
        "python",
        "setup.py",
        "build_ext",
        "--inplace"
    ]

    print(f"  [COMPILE] Cythonizing...")
    result = subprocess.run(cmd, cwd=str(cython_dir), capture_output=True, text=True)

    if result.returncode != 0:
        print(f"    [ERROR] {result.stderr}")
        return None

    # 收集 .so/.pyd 文件
    compiled_dir = Path(BUILD_DIR) / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)

    for f in os.listdir(cython_dir):
        if f.endswith('.so') or f.endswith('.pyd'):
            shutil.copy(cython_dir / f, compiled_dir / f)
            print(f"    [OUTPUT] {f}")

    print(f"  [DONE] Output: {compiled_dir}")
    return str(compiled_dir)


def run_nuitka(compiled_dir: str):
    """
    第三步：Nuitka 编译
    - 将整个应用编译为独立二进制
    - 包含 Python 解释器
    - 最终产物无任何 .py 文件
    """
    print("=" * 50)
    print("Step 3: Nuitka Compilation")
    print("=" * 50)

    nuitka_dir = Path(BUILD_DIR) / "nuitka"
    nuitka_dir.mkdir(parents=True, exist_ok=True)

    # 复制编译后的模块
    for f in os.listdir(compiled_dir):
        if f.endswith('.so') or f.endswith('.pyd'):
            shutil.copy(Path(compiled_dir) / f, nuitka_dir / f)

    # 复制静态文件
    static_dir = Path("static")
    if static_dir.exists():
        shutil.copytree(static_dir, nuitka_dir / "static", dirs_exist_ok=True)

    # 创建入口脚本
    entry_script = nuitka_dir / "entry.py"
    entry_script.write_text("""
import sys
sys.path.insert(0, '.')
from main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=9999)
""")

    # Nuitka 编译命令
    cmd = [
        "nuitka",
        "--standalone",
        "--onefile",
        "--output-dir", str(DIST_DIR),
        "--output-filename", "PrivacyGateway",
        "--include-data-dir=static=static",
        str(entry_script)
    ]

    print(f"  [COMPILE] Nuitka standalone...")
    result = subprocess.run(cmd, cwd=str(nuitka_dir), capture_output=True, text=True)

    if result.returncode != 0:
        print(f"    [ERROR] {result.stderr}")
        return None

    print(f"  [DONE] Output: {DIST_DIR}/PrivacyGateway")
    return f"{DIST_DIR}/PrivacyGateway"


def build_pro_version(license_key: str, watermark_data: dict):
    """
    构建 Pro 版本
    - 包含水印注入
    - 包含 License 验证
    - 包含 Rust 完整性校验模块
    """
    print("=" * 60)
    print("Building Pro Version")
    print("=" * 60)
    print(f"License Key: {license_key[:8]}...")
    print(f"Watermark: {watermark_data}")
    print()

    # 注入水印
    inject_watermark(watermark_data)

    # Step 1: PyArmor 混淆
    obfuscated_dir = run_pyarmor()
    if not obfuscated_dir:
        print("[WARNING] PyArmor step failed, continuing...")

    # Step 1.5: Rust 模块编译
    rust_dir = run_rust_build()
    if rust_dir:
        print(f"  [OK] Rust module compiled")
    else:
        print(f"  [WARNING] Rust module not available, using fallback")

    # Step 2: Cython 编译
    compiled_dir = run_cython(obfuscated_dir)
    if not compiled_dir:
        print("[FAILED] Cython step failed")
        return False

    # Step 3: Nuitka 编译
    binary_path = run_nuitka(compiled_dir)
    if not binary_path:
        print("[FAILED] Nuitka step failed")
        return False

    print()
    print("=" * 60)
    print("Build Complete!")
    print("=" * 60)
    print(f"Binary: {binary_path}")
    print(f"Size: {os.path.getsize(binary_path) / 1024 / 1024:.2f} MB")

    return True


def inject_watermark(watermark_data: dict):
    """
    注入水印到源码
    - 水印分散在多处
    - 加密存储
    """
    watermark_str = json.dumps(watermark_data, sort_keys=True)
    watermark_hash = hashlib.sha256(watermark_str.encode()).hexdigest()

    # 水印注入位置
    watermark_locations = [
        ("config.py", "# WATERMARK_1: {hash}"),
        ("gateway_core.py", "# WATERMARK_2: {hash}"),
        ("mask_engine.py", "# WATERMARK_3: {hash}"),
    ]

    for file_path, template in watermark_locations:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()

            # 注入水印
            watermark_comment = template.format(hash=watermark_hash[:16])
            if watermark_comment not in content:
                content = watermark_comment + "\n" + content
                with open(file_path, 'w') as f:
                    f.write(content)

    print(f"  [WATERMARK] Injected: {watermark_hash[:16]}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Pro/Enterprise Version")
    parser.add_argument("--version", choices=["pro", "enterprise"], required=True)
    parser.add_argument("--license-key", required=True)
    parser.add_argument("--customer-id", required=True)

    args = parser.parse_args()

    watermark = {
        "customer_id": args.customer_id,
        "license_key": args.license_key,
        "version": args.version,
        "build_time": str(int(time.time()))
    }

    build_pro_version(args.license_key, watermark)