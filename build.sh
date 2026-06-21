#!/bin/bash
# =============================================================================
#  AI Privacy Gateway — Build Script
# =============================================================================
#  Cross-platform build: CLI binary (all platforms) + .dmg (macOS only)
# =============================================================================
set -euo pipefail

echo "========================================"
echo "  AI Privacy Gateway - Build Script"
echo "========================================"
echo ""

# ── Detect OS ──────────────────────────────────────────────────────────────
OS="$(uname)"
echo "[Info] Platform: ${OS}"

# ── Install Dependencies ───────────────────────────────────────────────────
echo "[1/3] Installing dependencies..."
pip install -r requirements.txt -q
echo "[OK]  Dependencies installed"
echo ""

# ── Build Executable ───────────────────────────────────────────────────────
echo "[2/3] Building executable with PyInstaller..."
pyinstaller --clean --noconfirm PrivacyGateway.spec
echo "[OK]  PyInstaller build complete"
echo ""

# ── Build macOS .dmg (macOS only) ──────────────────────────────────────────
if [[ "${OS}" == "Darwin" ]]; then
    echo "[3/3] Building macOS .dmg package..."
    if [[ -f "packaging/macos/build_dmg.sh" ]]; then
        bash packaging/macos/build_dmg.sh
    else
        echo "[WARN] packaging/macos/build_dmg.sh not found — skipping DMG creation"
    fi
else
    echo "[3/3] Skipping DMG (not macOS)"
fi

echo ""
echo "========================================"
echo "  Build Complete"
echo "========================================"
echo ""
echo "  Binary: dist/PrivacyGateway"

if [[ "${OS}" == "Darwin" ]]; then
    echo "  DMG:    dist/AI-Privacy-Gateway-*.dmg"
    echo ""
    echo "  To distribute, copy the .dmg file from dist/"
    echo "  Users open it and drag the app to Applications."
fi

echo ""
