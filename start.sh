#!/usr/bin/env bash
# =============================================================================
#  AI Privacy Gateway — Start Script (macOS / Linux)
# =============================================================================
#  Usage:
#    ./start.sh              Interactive wizard
#    ./start.sh --non-interactive   Non-interactive mode (defaults)
#    ./start.sh --port 9999         Custom port
# =============================================================================
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Check if venv exists ────────────────────────────────────────────────────
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/activate" ]; then
    echo -e "${YELLOW}[WARN]${RESET} Virtual environment (.venv) not found."
    echo ""
    echo "  Please run the installer first:"
    echo ""
    echo "    ./install.sh"
    echo ""
    echo "  Or manually set up:"
    echo "    python3 -m venv .venv"
    echo "    source .venv/bin/activate"
    echo "    pip install -r requirements.txt"
    echo ""
    exit 1
fi

# ── Check Python ────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}[ERROR]${RESET} Python not found. Please install Python 3.8+."
    echo "  https://www.python.org/downloads/"
    exit 1
fi

# ── Check Python version ────────────────────────────────────────────────────
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    echo -e "${RED}[ERROR]${RESET} Python 3.8+ required, found: $PYTHON $PY_VER"
    exit 1
fi

# ── Check if port 9999 is in use ────────────────────────────────────────────
echo -e "${BOLD}[1/3]${RESET} Checking port 9999..."

if command -v ss &>/dev/null; then
    PORT_CHECK="ss -tlnp sport = :9999"
elif command -v lsof &>/dev/null; then
    PORT_CHECK="lsof -i :9999 -sTCP:LISTEN 2>/dev/null"
else
    PORT_CHECK="netstat -an | grep :9999.*LISTEN"
fi

if eval "$PORT_CHECK" 2>/dev/null | grep -q .; then
    echo -e "  ${YELLOW}[WARN]${RESET} Port 9999 is already in use."
    echo ""
    echo "  Another gateway instance may be running, or another service"
    echo "  is using that port."
    echo ""
    echo "  To change the port, edit the LISTEN_PORT in .env."
    echo ""
    read -rp "  Continue anyway? [y/N] " reply
    if [[ ! "$reply" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "  ${GREEN}[OK]${RESET} Port 9999 is available"
fi
echo ""

# ── Check .env exists ───────────────────────────────────────────────────────
echo -e "${BOLD}[2/3]${RESET} Checking configuration..."
if [ -f ".env" ]; then
    echo -e "  ${GREEN}[OK]${RESET} .env configuration found"
else
    echo -e "  ${YELLOW}[WARN]${RESET} .env file not found"
    echo ""
    if [ -f ".env.example" ]; then
        echo "  Generating from .env.example..."
        cp .env.example .env
        # Generate secure secrets inline
        ADMIN_PW=$($PYTHON -c "import secrets; pw=secrets.token_urlsafe(12); open('.env','a').write(f'ADMIN_PASSWORD={pw}\n'); print(pw)")
        JWT_SECRET=$($PYTHON -c "import secrets; s=secrets.token_hex(32); open('.env','a').write(f'JWT_SECRET={s}\n')")
        echo -e "  ${GREEN}[OK]${RESET} .env created with auto-generated secrets"
        echo ""
        echo -e "  Admin password: ${CYAN}$ADMIN_PW${RESET}"
    else
        echo -e "  ${RED}[ERROR]${RESET} No .env or .env.example found."
        echo "  Please run install.sh first."
        exit 1
    fi
fi
echo ""

# ── Activate venv and start ─────────────────────────────────────────────────
echo -e "${BOLD}[3/3]${RESET} Starting gateway..."
echo ""
echo "============================================================"
echo -e "  ${GREEN}Starting AI Privacy Gateway...${RESET}"
echo "============================================================"
echo ""
echo "  Dashboard:   http://localhost:9999"
echo "  Health:      http://localhost:9999/health"
echo ""
echo "  Press Ctrl+C to stop"
echo ""
echo "============================================================"
echo ""

# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONIOENCODING=utf-8

# If arguments were passed, forward to start.py
if [ $# -gt 0 ]; then
    exec "$PYTHON" start.py "$@"
else
    # Default: start directly with main.py for cleaner output
    exec "$PYTHON" main.py
fi
