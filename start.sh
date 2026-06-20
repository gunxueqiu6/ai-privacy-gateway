#!/usr/bin/env bash
# AI Privacy Gateway - 一键启动脚本 (macOS/Linux)
set -e

# 颜色
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

# 检查 Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}[ERROR] 未找到 Python，请先安装 Python 3.8+${RESET}"
    echo "        https://www.python.org/downloads/"
    exit 1
fi

# 检查 Python 版本 (通过 Python 自身，兼容 macOS BSD grep)
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    echo -e "${RED}[ERROR] 需要 Python 3.8 或更高版本，当前: $PYTHON $PY_VER${RESET}"
    exit 1
fi

echo -e "${CYAN}============================================${RESET}"
echo -e "${CYAN}  AI Privacy Gateway - 一键启动${RESET}"
echo -e "${CYAN}============================================${RESET}"
echo ""

if [ $# -eq 0 ]; then
    exec "$PYTHON" start.py --auto
else
    exec "$PYTHON" start.py "$@"
fi
