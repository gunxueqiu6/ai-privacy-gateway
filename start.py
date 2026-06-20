#!/usr/bin/env python3
"""
AI Privacy Gateway - 交互式启动向导

引导用户完成首次配置并启动网关。无额外依赖，仅标准库。

用法:
    python start.py             交互式模式
    python start.py --non-interactive  非交互模式（使用默认值）
    python start.py --port 9999       指定端口
"""
import argparse
import os
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# ── ANSI 颜色 ──────────────────────────────────────────────
_COLORS = {
    "green": "\033[92m",
    "cyan": "\033[96m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def c(text: str, *names: str) -> str:
    """Wrap text with ANSI color codes. No-op on Windows if terminal doesn't support it."""
    if not sys.stdout.isatty() or os.name == "nt" and "TERM" not in os.environ:
        return text
    for name in names:
        text = _COLORS.get(name, "") + text
    if names:
        text += _COLORS["reset"]
    return text


# ── 路径常量 ───────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent
ENV_PATH = PROJECT_DIR / ".env"
REQUIREMENTS_PATH = PROJECT_DIR / "requirements.txt"
MAIN_SCRIPT = PROJECT_DIR / "main.py"

# ── 提供商配置 ──────────────────────────────────────────────
PROVIDERS = {
    "1": {
        "name": "OpenAI",
        "url": "https://api.openai.com",
        "desc": c("OpenAI", "green"),
    },
    "2": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com",
        "desc": c("DeepSeek", "cyan"),
    },
    "3": {
        "name": "自定义",
        "url": None,
        "desc": c("自定义", "yellow"),
    },
}


# ── 工具函数 ───────────────────────────────────────────────


def println(text: str = "") -> None:
    """Print with newline, respecting ANSI codes."""
    # Handle Windows GBK encoding issues with Unicode characters
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", errors="replace").decode("ascii")
        print(safe)


def prompt(msg: str, default: str = "") -> str:
    """Ask user for input with optional default."""
    if default:
        msg = f"{msg} [{c(default, 'dim')}]: "
    else:
        msg = f"{msg}: "
    try:
        value = input(msg).strip()
    except (EOFError, KeyboardInterrupt):
        println()
        sys.exit(0)
    if not value and default:
        return default
    return value


def confirm(msg: str, default: bool = True) -> bool:
    """Yes/no prompt, return bool."""
    hint = "Y/n" if default else "y/N"
    while True:
        try:
            raw = input(f"{msg} [{c(hint, 'dim')}] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            println()
            sys.exit(0)
        if not raw:
            return default
        if raw in ("y", "yes", "是"):
            return True
        if raw in ("n", "no", "否"):
            return False
        println(f"{c('请输入 y 或 n。', 'yellow')}")


# ── 欢迎界靣 ───────────────────────────────────────────────


def print_welcome() -> None:
    """显示欢迎 Logo 和简介。"""
    logo = textwrap.dedent("""\
        +----------------------------------------------+
        |       AI Privacy Gateway  v1.1.0              |
        |       你的 AI 数据隐私防火墙                    |
        +----------------------------------------------+
    """)
    println()
    println(c(logo, "cyan"))
    println(c("在数据离开你的机器之前自动脱敏敏感信息，", "dim"))
    println(c("支持 OpenAI / DeepSeek 等所有兼容接口。", "dim"))
    println()


# ── 环境检测 ───────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="AI Privacy Gateway 交互式启动向导",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            示例:
              python start.py                        交互式模式
              python start.py --non-interactive       非交互模式
              python start.py --port 8080             指定端口
              python start.py --no-install            跳过依赖安装
        """),
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="非交互模式，直接使用默认值启动",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9999,
        help="监听端口（默认: 9999）",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="跳过依赖安装",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已存在的 .env 文件",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="全自动模式：零配置，一键启动",
    )
    return parser.parse_args()


def check_python_version() -> None:
    """Ensure Python >= 3.8."""
    if sys.version_info < (3, 8):
        println()
        println(c("错误: 需要 Python 3.8 或更高版本。", "red", "bold"))
        println(f"当前版本: {sys.version}")
        println("请从 https://www.python.org/downloads/ 下载最新版本。")
        sys.exit(1)


def check_port(port: int) -> bool:
    """检测端口是否被占用，返回 True 表示可用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            return False
    return True


def find_process_on_port(port: int) -> str:
    """尝试找出占用端口的进程名，返回描述字符串。"""
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    pid = parts[-1] if parts else ""
                    if pid:
                        try:
                            proc = subprocess.run(
                                ["tasklist", "/fi", f"PID eq {pid}", "/nh"],
                                capture_output=True, text=True, timeout=5,
                            )
                            name = proc.stdout.strip().split()[0] if proc.stdout.strip() else pid
                            return f"PID {pid} ({name})"
                        except subprocess.TimeoutExpired:
                            return f"PID {pid}"
            return f"端口 {port}"
        except subprocess.TimeoutExpired:
            return f"端口 {port}"
    else:
        for cmd in (
            ["lsof", "-i", f":{port}", "-sTCP:LISTEN", "-F", "pcn"],
            ["ss", "-tlnp", f"sport = :{port}"],
        ):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.stdout.strip():
                    return result.stdout.strip()[:60]
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
    return f"端口 {port}"


# ── 交互式配置 ─────────────────────────────────────────────


def pick_provider() -> tuple[str, str]:
    """选择 AI 服务提供商，返回 (name, url)。"""
    println(c("── 选择 AI 服务提供商 ──", "bold"))
    for key, p in PROVIDERS.items():
        url_str = p["url"] if p["url"] else "手动输入"
        println(f"  [{key}] {p['desc']}  ({c(url_str, 'dim')})")

    while True:
        choice = prompt("请选择", default="1")
        if choice in PROVIDERS:
            p = PROVIDERS[choice]
            if choice == "3":
                url = prompt("请输入目标 API 地址", default="https://api.openai.com")
                return ("自定义", url)
            return (p["name"], p["url"])
        println(c(f"无效选项: {choice}，请输入 1/2/3", "yellow"))


def prompt_upstream_api_key() -> str:
    """询问上游 API Key（可选）。"""
    println()
    println(c("── 上游 API 密钥（可选） ──", "bold"))
    println(c("如果你将网关当作转发代理使用，此处填写目标AI服务的 API Key。", "dim"))
    println(c("也可以在客户端直接传参，留空即可。", "dim"))
    return prompt("上游 API Key", default="")


def prompt_admin_password() -> str:
    """设置管理员密码。"""
    println()
    println(c("── 管理员密码 ──", "bold"))
    println(c("用于登录管理后台 (http://localhost:9999/admin)", "dim"))

    if not confirm("是否需要设置管理员密码?", default=True):
        return ""

    while True:
        pw = prompt("请输入管理密码（至少 8 位，留空自动生成）", default="")
        if not pw:
            generated = secrets.token_urlsafe(12)
            println(c(f"  自动生成密码: {generated}", "yellow"))
            println(c("  请立即保存此密码！", "bold"))
            return generated
        if len(pw) < 8:
            println(c("密码至少 8 位，请重新输入。", "yellow"))
            continue
        pw2 = prompt("请再次输入密码确认")
        if pw != pw2:
            println(c("两次密码不一致，请重新输入。", "yellow"))
            continue
        return pw


# ── .env 文件管理 ──────────────────────────────────────────


def _serialize_env(config: dict) -> str:
    """将配置字典序列化为 .env 格式字符串。"""
    lines = [
        "# AI Privacy Gateway 配置文件",
        "# 警告: 此文件包含敏感信息，切勿提交到版本控制系统！",
        f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "# ── AI 目标服务 ──",
        f"TARGET_LLM={config['TARGET_LLM']}",
        "",
        "# ── 网关配置 ──",
        f"LISTEN_PORT={config['LISTEN_PORT']}",
        "",
        "# ── JWT 密钥（用于管理后台认证） ──",
        f"JWT_SECRET={config['JWT_SECRET']}",
        "",
        "# ── 密码 ──",
    ]
    if config["ADMIN_PASSWORD"]:
        lines.append(f"ADMIN_PASSWORD={config['ADMIN_PASSWORD']}")
    else:
        lines.append("ADMIN_PASSWORD=")

    lines += [
        "",
        "# ── Vault 加密密钥（可选，为空时加密功能禁用） ──",
        f"VAULT_ENCRYPT_KEY={config['VAULT_ENCRYPT_KEY']}",
        "",
        "# ── 上游 API 密钥（可选） ──",
    ]
    if config["UPSTREAM_API_KEY"]:
        lines.append(f"UPSTREAM_API_KEY={config['UPSTREAM_API_KEY']}")
    else:
        lines.append("# UPSTREAM_API_KEY=")

    lines += [
        "",
        "# ── 数据库 ──",
        "DB_TYPE=sqlite",
        'DB_PATH=./vault_data/privacy_vault.db',
        "",
        "# ── 脱敏引擎 ──",
        "MASK_ENGINE_TYPE=regex",
        "",
        "# ============================================================",
        "# 安全提醒:",
        "# 1. 不要将此文件提交到 Git",
        "# 2. JWT_SECRET 泄漏会导致他人伪造管理身份",
        "# 3. 如需更换密钥，删除此文件后重新运行 start.py",
        "# ============================================================",
    ]
    return "\n".join(lines) + "\n"


def write_env_file(config: dict) -> None:
    """将配置写入 .env 文件。"""
    ENV_PATH.write_text(_serialize_env(config), encoding="utf-8")
    println(c("  [+] 配置文件已写入 .env", "green"))


def load_dotenv() -> None:
    """将 .env 文件中的变量加载到 os.environ。"""
    if not ENV_PATH.exists():
        return
    with ENV_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # 移除引号
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            os.environ[key] = value


def handle_existing_env(force: bool = False) -> bool:
    """处理已存在的 .env 文件。返回 True 表示继续（覆盖），False 表示跳过交互。"""
    if not ENV_PATH.exists():
        return True

    println(c("检测到已存在的 .env 配置文件。", "yellow"))
    if force:
        println(c("  --force 参数已指定，将覆盖现有配置。", "dim"))
        return True

    return confirm("是否覆盖现有配置?", default=False)


# ── 依赖安装 ───────────────────────────────────────────────


def check_dependencies() -> list[str]:
    """检查关键依赖是否已安装，返回缺失的包名列表。"""
    required = ["fastapi", "uvicorn", "httpx", "bcrypt"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def install_dependencies(missing: list[str], no_install: bool = False) -> bool:
    """安装缺失的依赖，返回 True 表示成功。"""
    if not missing:
        return True

    println()
    println(c(f"── 安装缺失依赖: {', '.join(missing)} ──", "bold"))

    if no_install:
        println(c("  --no-install 已指定，跳过依赖安装。", "yellow"))
        println(c("  请手动运行: pip install -r requirements.txt", "yellow"))
        return False

    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)]
    println(c(f"  运行: pip install -r requirements.txt", "dim"))

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            println()
            println(c("依赖安装失败。", "red", "bold"))
            println("请尝试手动安装:")
            println(f"  {shlex.join(cmd)}")
            return False
        println(c("  [+] 依赖安装完成", "green"))
        return True
    except FileNotFoundError:
        println()
        println(c("错误: 找不到 pip。请确保 Python 已正确安装。", "red"))
        println("尝试: python -m ensurepip --upgrade")
        return False


# ── 配置摘要 ───────────────────────────────────────────────


def format_config_summary(config: dict) -> str:
    """生成配置摘要文本。"""
    pw_display = (
        c(config["ADMIN_PASSWORD"], "yellow", "bold")
        if config["ADMIN_PASSWORD"]
        else c("自动生成随机密码", "dim")
    )
    api_key_display = (
        c(config["UPSTREAM_API_KEY"][:8] + "****", "dim")
        if config["UPSTREAM_API_KEY"]
        else c("未设置", "dim")
    )
    lines = [
        "",
        c("  +------------------------------------------+", "cyan"),
        c("  | 配置摘要                                 |", "cyan", "bold"),
        c("  +------------------------------------------+", "cyan"),
        f"     目标 AI:    {c(config['provider_name'], 'green')} -> {c(config['TARGET_LLM'], 'cyan')}",
        f"    监听端口:    {config['LISTEN_PORT']}",
        f"    管理员密码:  {pw_display}",
        f"    上游 API Key: {api_key_display}",
        f"    JWT 密钥:    {c('已生成', 'green')} ({len(config['JWT_SECRET'])} 位)",
        f"    Vault 密钥:  {c('已生成', 'green')} ({len(config['VAULT_ENCRYPT_KEY'])} 位)",
        f"    数据库:      {config['DB_PATH']}",
        "",
    ]
    return "\n".join(lines)


def print_security_reminder() -> None:
    """显示安全提醒。"""
    reminder = textwrap.dedent("""\

        +----------------------------------------------+
        |  [!] 安全提醒                                 |
        |                                              |
        |  1. .env 文件包含敏感信息                      |
        |     不要提交到版本控制系统！                    |
        |                                              |
        |  2. 默认已添加到 .gitignore                    |
        |     请确认 .env 不会出现在你的 commit 中        |
        |                                              |
        |  3. 首次登录管理后台后建议修改密码               |
        +----------------------------------------------+
    """)
    println(c(reminder, "yellow"))


# ── 非交互模式 ─────────────────────────────────────────────


def gen_config_non_interactive(args: argparse.Namespace) -> dict:
    """非交互模式：生成全默认配置。"""
    return {
        "provider_name": "OpenAI",
        "TARGET_LLM": "https://api.openai.com",
        "LISTEN_PORT": args.port,
        "ADMIN_PASSWORD": secrets.token_urlsafe(12),
        "JWT_SECRET": secrets.token_hex(32),
        "VAULT_ENCRYPT_KEY": secrets.token_hex(32),
        "UPSTREAM_API_KEY": "",
        "DB_PATH": "./vault_data/privacy_vault.db",
    }


def gen_config_auto(args: argparse.Namespace) -> dict:
    """全自动模式：自动寻找可用端口，自动生成所有密钥，零交互。"""
    port = args.port
    if not check_port(port):
        # 端口被占用，自动寻找下一个可用端口
        proc_info = find_process_on_port(port)
        println(c(f"  端口 {port} 已被占用 ({proc_info})，自动切换...", "yellow"))
        for offset in range(1, 100):
            candidate = port + offset
            if check_port(candidate):
                port = candidate
                println(c(f"  已自动选择端口: {port}", "green"))
                break
        else:
            println(c("错误: 找不到可用端口。", "red", "bold"))
            sys.exit(1)

    return {
        "provider_name": "OpenAI",
        "TARGET_LLM": "https://api.openai.com",
        "LISTEN_PORT": port,
        "ADMIN_PASSWORD": secrets.token_urlsafe(12),
        "JWT_SECRET": secrets.token_hex(32),
        "VAULT_ENCRYPT_KEY": secrets.token_hex(32),
        "UPSTREAM_API_KEY": "",
        "DB_PATH": "./vault_data/privacy_vault.db",
    }


def validate_port(s: str) -> int | None:
    """Validate port number string, return int or None."""
    try:
        p = int(s)
        return p if 1 <= p <= 65535 else None
    except ValueError:
        return None


def prompt_port(default: int) -> int:
    """Prompt for port number with validation."""
    while True:
        port_str = prompt("监听端口", default=str(default))
        validated = validate_port(port_str)
        if validated is not None:
            return validated
        println(c("端口必须是 1-65535 之间的数字", "yellow"))


def gen_config_interactive(args: argparse.Namespace) -> dict:
    """交互模式：通过问答收集配置。"""
    println()
    provider_name, provider_url = pick_provider()

    println()
    println(c("── 网关端口 ──", "bold"))
    println(c("默认端口 9999，如果被占用可以更换。", "dim"))
    port = args.port
    if not check_port(port):
        proc_info = find_process_on_port(port)
        println(c(f"  端口 {port} 已被占用 ({proc_info})", "yellow"))
        port = prompt_port(port + 1)
    else:
        port = prompt_port(port)

    upstream_api_key = prompt_upstream_api_key()
    admin_password = prompt_admin_password()

    return {
        "provider_name": provider_name,
        "TARGET_LLM": provider_url,
        "LISTEN_PORT": port,
        "ADMIN_PASSWORD": admin_password,
        "JWT_SECRET": secrets.token_hex(32),
        "VAULT_ENCRYPT_KEY": secrets.token_hex(32),
        "UPSTREAM_API_KEY": upstream_api_key,
        "DB_PATH": "./vault_data/privacy_vault.db",
    }


# ── 启动网关 ───────────────────────────────────────────────


def start_gateway(config: dict) -> None:
    """启动网关服务（通过 subprocess 运行 main.py）。"""
    port = config["LISTEN_PORT"]

    println()
    println(c("── 正在启动 AI Privacy Gateway ──", "bold"))
    println()

    # 创建 vault_data 目录
    vault_dir = PROJECT_DIR / "vault_data"
    vault_dir.mkdir(exist_ok=True)

    # 启动子进程
    env = os.environ.copy()
    env["JWT_SECRET"] = config["JWT_SECRET"]
    env["VAULT_ENCRYPT_KEY"] = config["VAULT_ENCRYPT_KEY"]
    env["TARGET_LLM"] = config["TARGET_LLM"]
    env["LISTEN_PORT"] = str(config["LISTEN_PORT"])
    env["ADMIN_PASSWORD"] = config["ADMIN_PASSWORD"]
    if config["UPSTREAM_API_KEY"]:
        env["UPSTREAM_API_KEY"] = config["UPSTREAM_API_KEY"]

    proc = subprocess.Popen(
        [sys.executable, str(MAIN_SCRIPT)],
        env=env,
        cwd=PROJECT_DIR,
    )

    println(c("  [+] 网关服务已启动！", "green"))
    println()
    println(f"  API 地址:       {c('http://localhost:' + str(port), 'cyan', 'bold')}")
    println(f"  管理后台:       {c('http://localhost:' + str(port) + '/admin', 'cyan', 'bold')}")
    println(f"  目标 AI 服务:   {c(config['TARGET_LLM'], 'cyan')}")
    println()
    println(c("  将你的 AI 客户端 API 地址改为:", "bold"))
    println(c(f"    http://localhost:{port}/v1", "cyan", "bold"))
    println()
    println(c("  按 Ctrl+C 停止服务", "dim"))
    println()

    try:
        proc.wait()
    except KeyboardInterrupt:
        println()
        println(c("正在停止服务...", "yellow"))
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        println(c("  [+] 服务已停止", "green"))


# ── Main ────────────────────────────────────────────────────


def main() -> None:
    """主入口。"""
    args = parse_args()
    check_python_version()

    # ── 全自动模式 ──────────────────────────────────
    if args.auto:
        # 如果 .env 已存在，加载并直接启动
        if ENV_PATH.exists():
            println(c("检测到已存在的配置文件，直接启动。", "dim"))
            load_dotenv()
            config = {
                "provider_name": "OpenAI",
                "TARGET_LLM": os.environ.get("TARGET_LLM", "https://api.openai.com"),
                "LISTEN_PORT": int(os.environ.get("LISTEN_PORT", str(args.port))),
                "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD", ""),
                "JWT_SECRET": os.environ.get("JWT_SECRET", ""),
                "VAULT_ENCRYPT_KEY": os.environ.get("VAULT_ENCRYPT_KEY", ""),
                "UPSTREAM_API_KEY": os.environ.get("UPSTREAM_API_KEY", ""),
                "DB_PATH": os.environ.get("DB_PATH", "./vault_data/privacy_vault.db"),
            }
            # 显示已有密码，方便用户找回
            if config["ADMIN_PASSWORD"]:
                println()
                println(c("  管理员密码: ", "dim") + c(config["ADMIN_PASSWORD"], "yellow", "bold"))
                println(c("  (从 .env 中读取，如已遗忘可删除 .env 后重新运行生成)", "dim"))
                println()
        else:
            println(c("正在自动配置...", "dim"))
            config = gen_config_auto(args)
            write_env_file(config)
            # 显示简洁的使用说明
            println()
            println(c("  +------------------------------------------+", "cyan"))
            println(c("  |  AI Privacy Gateway 配置完成              |", "cyan", "bold"))
            println(c("  +------------------------------------------+", "cyan"))
            println()
            println(f"  API 地址:   {c('http://localhost:' + str(config['LISTEN_PORT']) + '/v1', 'cyan', 'bold')}")
            println(f"  管理后台:   {c('http://localhost:' + str(config['LISTEN_PORT']) + '/admin', 'cyan')}")
            if config["ADMIN_PASSWORD"]:
                println(f"  管理员密码: {c(config['ADMIN_PASSWORD'], 'yellow', 'bold')}")
                println(c("            请复制保存此密码！", "yellow"))
            println()
            println(c("  将 AI 客户端的 API 地址改为上方地址即可使用。", "dim"))
            println()

        # 安装依赖
        missing = check_dependencies()
        if missing:
            println(c(f"安装依赖: {', '.join(missing)}...", "dim"))
            if not install_dependencies(missing, no_install=args.no_install):
                println(c("依赖安装失败，请手动运行: pip install -r requirements.txt", "red"))
                sys.exit(1)

        start_gateway(config)
        return

    # ── 非交互模式 ──────────────────────────────────
    if args.non_interactive:
        config = gen_config_non_interactive(args)
        write_env_file(config)
        print_security_reminder()

        missing = check_dependencies()
        install_dependencies(missing, no_install=args.no_install)

        missing_after = check_dependencies()
        if missing_after:
            println()
            println(c("错误: 依赖未安装完整，无法启动。", "red", "bold"))
            println(f"缺失: {', '.join(missing_after)}")
            println(f"请运行: pip install -r requirements.txt")
            sys.exit(1)

        start_gateway(config)
        return

    # ── 交互模式 ──────────────────────────────────
    print_welcome()
    proceed = handle_existing_env(force=args.force)
    if not proceed:
        println(c("保留现有配置，直接启动。", "dim"))

    config = gen_config_interactive(args)
    println(format_config_summary(config))
    if not confirm("以上配置是否正确，是否继续?", default=True):
        println(c("已取消。", "yellow"))
        sys.exit(0)

    write_env_file(config)
    print_security_reminder()

    missing = check_dependencies()
    install_dependencies(missing, no_install=args.no_install)

    missing_after = check_dependencies()
    if missing_after:
        println()
        println(c("错误: 依赖未安装完整，无法启动。", "red", "bold"))
        println(f"缺失: {', '.join(missing_after)}")
        println(f"请运行: pip install -r requirements.txt")
        sys.exit(1)

    start_gateway(config)


if __name__ == "__main__":
    main()
