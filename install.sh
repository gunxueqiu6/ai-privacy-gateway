#!/usr/bin/env bash
# =============================================================================
#  AI Privacy Gateway — One-Click Installer (macOS / Linux)
# =============================================================================
#  Usage:
#    chmod +x install.sh && ./install.sh
# =============================================================================
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Banner ──────────────────────────────────────────────────────────────────
echo "============================================================"
echo "  AI Privacy Gateway - One-Click Installer"
echo "============================================================"
echo ""
echo "  This script will:"
echo "    1. Check Python 3.10+"
echo "    2. Create a virtual environment"
echo "    3. Install Python dependencies"
echo "    4. Generate .env config with secure secrets"
echo ""
echo "============================================================"
echo ""

# ── Step 1: Detect Python ──────────────────────────────────────────────────
echo -e "${BOLD}[1/5]${RESET} Checking Python environment..."

PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "  ${RED}[FAIL]${RESET} Python not found."
    echo ""
    echo "  Please install Python 3.10+ from:"
    echo "    https://www.python.org/downloads/"
    echo ""
    echo "  On macOS with Homebrew:"
    echo "    brew install python@3.12"
    echo ""
    echo "  On Ubuntu/Debian:"
    echo "    sudo apt update && sudo apt install python3 python3-venv python3-pip"
    echo ""
    exit 1
fi

# Check version >= 3.10
PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo -e "  ${RED}[FAIL]${RESET} Python 3.10+ required, found: $PYTHON $PY_VER"
    echo ""
    echo "  Please install a newer version of Python."
    exit 1
fi

echo -e "  ${GREEN}[OK]${RESET} Python $PY_VER found: $PYTHON"
echo ""

# ── Step 2: Create Virtual Environment ─────────────────────────────────────
echo -e "${BOLD}[2/5]${RESET} Creating virtual environment..."

if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo -e "  ${GREEN}[SKIP]${RESET} .venv already exists"
else
    echo "  Creating .venv with $PYTHON..."
    "$PYTHON" -m venv .venv
    echo -e "  ${GREEN}[OK]${RESET} Virtual environment created"
fi
echo ""

# ── Step 3: Install Dependencies ────────────────────────────────────────────
echo -e "${BOLD}[3/5]${RESET} Installing dependencies..."

# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip -q 2>/dev/null || echo -e "  ${YELLOW}[WARN]${RESET} pip upgrade failed, continuing"

# Install requirements
if [ ! -f "requirements.txt" ]; then
    echo -e "  ${RED}[FAIL]${RESET} requirements.txt not found"
    echo "  Make sure you are in the project root directory."
    exit 1
fi

pip install -r requirements.txt -q
echo -e "  ${GREEN}[OK]${RESET} Dependencies installed"
echo ""

# ── Step 4: Generate .env File ──────────────────────────────────────────────
echo -e "${BOLD}[4/5]${RESET} Generating configuration..."

if [ -f ".env" ]; then
    echo -e "  ${GREEN}[SKIP]${RESET} .env already exists"
    echo ""
    echo "  To regenerate, delete .env and re-run this script."
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "  ${GREEN}[OK]${RESET} .env created from .env.example"
    else
        echo -e "  ${YELLOW}[WARN]${RESET} .env.example not found, creating minimal config..."
        cat > .env << 'ENVEOF'
# AI Privacy Gateway — Configuration
TARGET_LLM=https://api.openai.com
LISTEN_PORT=9999
DB_PATH=./vault_data/privacy_vault.db
DB_TYPE=sqlite
MASK_ENGINE_TYPE=regex
UPSTREAM_API_KEY=
ENVEOF
        echo -e "  ${GREEN}[OK]${RESET} Minimal .env created"
    fi

    # Generate secure random values
    ADMIN_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(12))")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # Inject into .env
    if grep -q "^ADMIN_PASSWORD=" .env; then
        # Replace empty or placeholder value
        sed -i.bak "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=$ADMIN_PW/" .env
        rm -f .env.bak
    else
        echo "" >> .env
        echo "# Admin dashboard password" >> .env
        echo "ADMIN_PASSWORD=$ADMIN_PW" >> .env
    fi

    echo "" >> .env
    echo "# Auto-generated JWT secret" >> .env
    echo "JWT_SECRET=$JWT_SECRET" >> .env

    echo ""
    echo -e "  ${GREEN}Admin password: ${CYAN}$ADMIN_PW${RESET}"
    echo "  Save this password — you'll need it to log into the dashboard."
    echo ""
fi
echo ""

# ── Step 5: Done ────────────────────────────────────────────────────────────
echo -e "${BOLD}[5/5]${RESET} Finalizing..."
echo ""

echo "============================================================"
echo -e "  ${GREEN}Installation Complete!${RESET}"
echo "============================================================"
echo ""
echo "  Start the gateway:"
echo ""
echo "    ./start.sh"
echo "    # or"
echo "    python start.py"
echo ""
echo "  Then open in your browser:"
echo "    http://localhost:9999          — Dashboard"
echo "    http://localhost:9999/health   — Health check"
echo ""
echo "  Admin password: ${CYAN}$ADMIN_PW${RESET}"
echo ""
echo "  To change settings, edit .env and restart."
echo ""
echo "============================================================"
echo ""
