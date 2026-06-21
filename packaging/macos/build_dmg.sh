#!/usr/bin/env bash
# =============================================================================
#  AI Privacy Gateway — macOS .dmg 构建脚本
# =============================================================================
#  Produces:  dist/AI-Privacy-Gateway-<version>.dmg
#
#  Prerequisites:
#    - macOS 11.0+
#    - Xcode Command Line Tools (xcode-select --install)
#    - Python 3.10+
#    - PyInstaller (pip install pyinstaller)
#
#  Usage:
#    bash packaging/macos/build_dmg.sh
# =============================================================================
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────
VERSION="2.0.0"
SHORT_VERSION="2.0"
APP_NAME="AI Privacy Gateway"
BUNDLE_ID="com.aiprivacygateway.app"
DMG_NAME="AI-Privacy-Gateway-${VERSION}.dmg"

# ── Paths (relative to project root) ───────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DIST_DIR="${PROJECT_DIR}/dist"
BUILD_DIR="${PROJECT_DIR}/build"
PACKAGING_DIR="${PROJECT_DIR}/packaging/macos"
STAGING_DIR="${BUILD_DIR}/dmg-staging"
ICONSET_DIR="${BUILD_DIR}/AppIcon.iconset"

# PyInstaller output binary
PYI_BINARY="${DIST_DIR}/PrivacyGateway"

# .app bundle paths
APP_BUNDLE="${STAGING_DIR}/${APP_NAME}.app"
APP_CONTENTS="${APP_BUNDLE}/Contents"
APP_MACOS="${APP_CONTENTS}/MacOS"
APP_RESOURCES="${APP_CONTENTS}/Resources"

# Python command (resolved during check_prerequisites)
PY_CMD=""

# ── Colors ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()    { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
fail()  { echo -e "${RED}[FAIL]${RESET}  $*"; exit 1; }

# ── Check Prerequisites ────────────────────────────────────────────────────
check_prerequisites() {
    info "Checking prerequisites..."

    # macOS check
    if [[ "$(uname)" != "Darwin" ]]; then
        fail "This script must be run on macOS."
    fi

    # OS version check (11.0+)
    local os_ver
    os_ver=$(sw_vers -productVersion 2>/dev/null || echo "0.0")
    if [[ "$(echo "$os_ver" | cut -d. -f1)" -lt 11 ]]; then
        fail "macOS 11.0 (Big Sur) or later required. Current: $os_ver"
    fi
    ok "macOS $os_ver"

    # Python check — store in global PY_CMD
    PY_CMD=""
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            PY_CMD="$cmd"
            break
        fi
    done
    if [[ -z "$PY_CMD" ]]; then
        fail "Python not found. Please install Python 3.10+ from https://www.python.org/downloads/"
    fi

    local py_ver
    py_ver=$($PY_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    local py_major
    py_major=$(echo "$py_ver" | cut -d. -f1)
    local py_minor
    py_minor=$(echo "$py_ver" | cut -d. -f2)
    if [[ "$py_major" -lt 3 ]] || { [[ "$py_major" -eq 3 ]] && [[ "$py_minor" -lt 10 ]]; }; then
        fail "Python 3.10+ required. Current: $PY_CMD $py_ver"
    fi
    ok "Python $py_ver ($PY_CMD)"

    # PyInstaller check
    if ! $PY_CMD -c "import PyInstaller" 2>/dev/null; then
        fail "PyInstaller not found. Run: pip install pyinstaller"
    fi
    ok "PyInstaller available"

    # Required macOS tools
    for tool in hdiutil iconutil sips; do
        if ! command -v "$tool" &>/dev/null; then
            fail "Required tool not found: $tool"
        fi
    done
    ok "All required tools available"

    # PrivacyGateway.spec exists
    if [[ ! -f "${PROJECT_DIR}/PrivacyGateway.spec" ]]; then
        fail "PrivacyGateway.spec not found in project root."
    fi
    ok "PrivacyGateway.spec found"

    echo ""
}

# ── Step 1: Build executable with PyInstaller ──────────────────────────────
step_pyinstaller() {
    info "[1/5] Building executable with PyInstaller..."
    cd "$PROJECT_DIR"

    # Install deps first
    $PY_CMD -m pip install -r requirements.txt -q
    ok "Dependencies installed"

    $PY_CMD -m PyInstaller --clean --noconfirm PrivacyGateway.spec
    ok "PyInstaller build complete"

    if [[ ! -f "$PYI_BINARY" ]]; then
        fail "PyInstaller did not produce expected binary: $PYI_BINARY"
    fi

    local file_size
    file_size=$(du -h "$PYI_BINARY" 2>/dev/null | cut -f1)
    ok "Binary found at: $PYI_BINARY ($file_size)"
    echo ""
}

# ── Step 2: Generate .app icon ─────────────────────────────────────────────
step_icon() {
    info "[2/5] Generating application icon..."

    # Clean previous
    rm -rf "$ICONSET_DIR"
    mkdir -p "$ICONSET_DIR"

    local icon_png="${BUILD_DIR}/app-icon-1024.png"

    # Generate a 1024x1024 RGBA PNG icon using Python (stdlib only).
    # Design: rounded-rect with blue-to-purple gradient background,
    # white shield outline with a dark-blue letter "P".
    info "  Rendering 1024x1024 icon with Python..."
    $PY_CMD -c "
import struct, zlib, math, os

W, H = 1024, 1024
pixels = bytearray(W * H * 4)

def fill_rounded_rect(r):
    \"\"\"Fill a gradient rounded-rect into pixels.\"\"\"
    for y in range(H):
        t = y / H
        # Blue -> Purple gradient
        r_col = int((0.20 + t * 0.30) * 255)
        g_col = int((0.35 - t * 0.12) * 255)
        b_col = int((0.85 - t * 0.05) * 255)
        for x in range(W):
            # Check if inside rounded rect
            inside = False
            if x >= r and x < W - r and y >= r and y < H - r:
                inside = True
            elif x < r and y < r:
                inside = (x - r)**2 + (y - r)**2 <= r*r
            elif x >= W - r and y < r:
                inside = (x - (W-1-r))**2 + (y - r)**2 <= r*r
            elif x < r and y >= H - r:
                inside = (x - r)**2 + (y - (H-1-r))**2 <= r*r
            elif x >= W - r and y >= H - r:
                inside = (x - (W-1-r))**2 + (y - (H-1-r))**2 <= r*r
            if inside:
                idx = (y * W + x) * 4
                pixels[idx] = r_col
                pixels[idx+1] = g_col
                pixels[idx+2] = b_col
                pixels[idx+3] = 255

def fill_circle(cx, cy, rad, r, g, b, a):
    \"\"\"Fill a circle with anti-aliased edges.\"\"\"
    x0 = max(0, int(cx - rad - 1))
    x1 = min(W-1, int(cx + rad + 1))
    y0 = max(0, int(cy - rad - 1))
    y1 = min(H-1, int(cy + rad + 1))
    r2 = rad * rad
    for y in range(y0, y1+1):
        for x in range(x0, x1+1):
            dx, dy = x - cx, y - cy
            d2 = dx*dx + dy*dy
            if d2 <= r2:
                idx = (y * W + x) * 4
                # Simple edge antialiasing: blend alpha near boundary
                edge = math.sqrt(d2)
                alpha = a
                if edge > rad - 1.5:
                    alpha = int(a * max(0, rad - edge + 1.5) / 1.5)
                if alpha > 0:
                    # Blend over background
                    bg_a = pixels[idx+3]
                    if bg_a > 0:
                        out_a = 255 - ((255 - alpha) * (255 - bg_a)) // 255
                        if out_a > 0:
                            pixels[idx] = (r * alpha + pixels[idx] * (255 - alpha)) // 255
                            pixels[idx+1] = (g * alpha + pixels[idx+1] * (255 - alpha)) // 255
                            pixels[idx+2] = (b * alpha + pixels[idx+2] * (255 - alpha)) // 255
                            pixels[idx+3] = out_a
                    else:
                        pixels[idx] = r
                        pixels[idx+1] = g
                        pixels[idx+2] = b
                        pixels[idx+3] = alpha

def fill_polygon(pts, r, g, b, a):
    \"\"\"Fill a polygon using scanline algorithm.\"\"\"
    ys = [p[1] for p in pts]
    min_y = max(0, min(ys))
    max_y = min(H-1, max(ys))
    n = len(pts)
    for y in range(min_y, max_y+1):
        xs = []
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i+1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                if y1 != y2:
                    x = int(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
                    xs.append(x)
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            for x in range(max(0, xs[i]), min(W, xs[i+1]+1)):
                idx = (y * W + x) * 4
                # Blend
                bg_a = pixels[idx+3]
                if bg_a > 0:
                    out_a = 255 - ((255 - a) * (255 - bg_a)) // 255
                    if out_a > 0:
                        pixels[idx] = (r * a + pixels[idx] * (255 - a)) // 255
                        pixels[idx+1] = (g * a + pixels[idx+1] * (255 - a)) // 255
                        pixels[idx+2] = (b * a + pixels[idx+2] * (255 - a)) // 255
                        pixels[idx+3] = out_a
                else:
                    pixels[idx] = r; pixels[idx+1] = g; pixels[idx+2] = b; pixels[idx+3] = a

# 1. Background: rounded rect with radius 180
fill_rounded_rect(180)

# 2. Shield shape — white, 65% opacity
cx = W // 2
cy = H // 2 - 10
sw = 380
sh = 460
top_y = cy - sh // 2
bot_y = cy + sh // 2

shield = [
    (cx - sw//2, top_y + 100),
    (cx - sw//2 + 40, top_y),
    (cx + sw//2 - 40, top_y),
    (cx + sw//2, top_y + 100),
    (cx + sw//2 + 30, cy - 20),
    (cx + sw//2 + 20, bot_y - 10),
    (cx + sw//2 - 20, bot_y),
    (cx, bot_y + 50),
    (cx, bot_y + 50),
    (cx - sw//2 + 20, bot_y),
    (cx - sw//2 - 20, bot_y - 10),
    (cx - sw//2 - 30, cy - 20),
]
fill_polygon(shield, 255, 255, 255, 172)

# 3. Rounded rectangle behind 'P' (inset shield area)
inset_r = 30
inset_x0 = cx - 90
inset_x1 = cx + 100
inset_y0 = cy - 150
inset_y1 = cy + 100
for y in range(max(0, inset_y0), min(H, inset_y1+1)):
    for x in range(max(0, inset_x0), min(W, inset_x1+1)):
        inside = False
        if x >= inset_x0 + inset_r and x < inset_x1 - inset_r and y >= inset_y0 and y < inset_y1:
            inside = True
        elif x < inset_x0 + inset_r and y < inset_y0 + inset_r:
            inside = (x - (inset_x0+inset_r))**2 + (y - (inset_y0+inset_r))**2 <= inset_r*inset_r
        elif x >= inset_x1 - inset_r and y < inset_y0 + inset_r:
            inside = (x - (inset_x1-1-inset_r))**2 + (y - (inset_y0+inset_r))**2 <= inset_r*inset_r
        elif x < inset_x0 + inset_r and y >= inset_y1 - inset_r:
            inside = (x - (inset_x0+inset_r))**2 + (y - (inset_y1-1-inset_r))**2 <= inset_r*inset_r
        elif x >= inset_x1 - inset_r and y >= inset_y1 - inset_r:
            inside = (x - (inset_x1-1-inset_r))**2 + (y - (inset_y1-1-inset_r))**2 <= inset_r*inset_r
        if inside:
            idx = (y * W + x) * 4
            pixels[idx] = min(255, pixels[idx] + 40)
            pixels[idx+1] = min(255, pixels[idx+1] + 40)
            pixels[idx+2] = min(255, pixels[idx+2] + 40)

# 4. Letter 'P' in dark blue
pcx = cx - 20
pcy = cy - 25
thick = 36

def put(x, y, r, g, b, a):
    if 0 <= x < W and 0 <= y < H:
        idx = (y * W + x) * 4
        bg_a = pixels[idx+3]
        if bg_a > 0:
            out_a = 255 - ((255 - a) * (255 - bg_a)) // 255
            if out_a > 0:
                pixels[idx] = (r * a + pixels[idx] * (255 - a)) // 255
                pixels[idx+1] = (g * a + pixels[idx+1] * (255 - a)) // 255
                pixels[idx+2] = (b * a + pixels[idx+2] * (255 - a)) // 255
                pixels[idx+3] = out_a
        else:
            pixels[idx] = r; pixels[idx+1] = g; pixels[idx+2] = b; pixels[idx+3] = a

# Vertical stroke of 'P'
for y in range(-140, 120):
    for t in range(-thick//2, thick//2):
        put(pcx + t, pcy + y, 25, 45, 110, 235)

# Top horizontal stroke
for x in range(-5, 80):
    for t in range(-thick//2, thick//2):
        put(pcx + x, pcy - 140 + t, 25, 45, 110, 235)

# Middle horizontal stroke
for x in range(-5, 80):
    for t in range(-thick//2, thick//2):
        put(pcx + x, pcy + t, 25, 45, 110, 235)

# Right curve of 'P' — circle segment
ccx = pcx + 50
ccy = pcy - 70
crad = 70
for angle_deg in range(-95, 96):
    rad = math.radians(angle_deg)
    for t in range(-thick//2, thick//2):
        rx = int(ccx + (crad + t) * math.cos(rad))
        ry = int(ccy + (crad + t) * math.sin(rad))
        put(rx, ry, 25, 45, 110, 235)

# Write PNG
def write_png(filepath):
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 6, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter byte = None
        raw.extend(pixels[y*W*4:(y+1)*W*4])
    compressed = zlib.compress(bytes(raw))
    with open(filepath, 'wb') as f:
        f.write(b'\\x89PNG\\r\\n\\x1a\\n')
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', compressed))
        f.write(chunk(b'IEND', b''))

write_png('${icon_png}')
print('Icon PNG generated: ${icon_png}')
"

    if [[ ! -f "$icon_png" ]]; then
        warn "Python icon generation failed. Generating fallback icon..."
        # Fallback: use a solid-color generic icon from the system
        cp "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericApplicationIcon.icns" \
           "${BUILD_DIR}/AppIcon.icns" 2>/dev/null || true
        ok "Fallback icon used (GenericApplicationIcon)"
        echo ""
        return
    fi

    # Create iconset from the 1024px PNG using sips
    info "  Creating iconset..."
    declare -A sizes=(
        ["icon_16x16.png"]="16"
        ["icon_32x32.png"]="32"
        ["icon_128x128.png"]="128"
        ["icon_256x256.png"]="256"
        ["icon_512x512.png"]="512"
        ["icon_1024x1024.png"]="1024"
        ["icon_16x16@2x.png"]="32"
        ["icon_32x32@2x.png"]="64"
        ["icon_128x128@2x.png"]="256"
        ["icon_256x256@2x.png"]="512"
        ["icon_512x512@2x.png"]="1024"
    )

    for file in "${!sizes[@]}"; do
        sips -z "${sizes[$file]}" "${sizes[$file]}" "$icon_png" \
            --out "${ICONSET_DIR}/${file}" &>/dev/null
    done

    # Convert iconset to .icns
    iconutil -c icns "$ICONSET_DIR" -o "${BUILD_DIR}/AppIcon.icns" 2>/dev/null
    if [[ ! -f "${BUILD_DIR}/AppIcon.icns" ]]; then
        warn "iconutil conversion failed. Will use PNG as fallback in the bundle."
    else
        ok "Icon generated: ${BUILD_DIR}/AppIcon.icns"
    fi
    echo ""
}

# ── Step 3: Create .app bundle ─────────────────────────────────────────────
step_app_bundle() {
    info "[3/5] Creating .app bundle..."

    # Clean staging
    rm -rf "$STAGING_DIR"
    mkdir -p "$APP_MACOS"
    mkdir -p "$APP_RESOURCES"

    # Copy PyInstaller binary into .app bundle (rename to app name)
    cp "$PYI_BINARY" "${APP_MACOS}/${APP_NAME}"
    chmod +x "${APP_MACOS}/${APP_NAME}"

    # Copy icon
    if [[ -f "${BUILD_DIR}/AppIcon.icns" ]]; then
        cp "${BUILD_DIR}/AppIcon.icns" "${APP_RESOURCES}/app.icns"
    fi

    # Create Info.plist
    cat > "${APP_CONTENTS}/Info.plist" <<- PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${SHORT_VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLISTEOF

    # Create PkgInfo (required by macOS)
    echo -n "APPL????" > "${APP_CONTENTS}/PkgInfo"

    # Verify bundle structure
    local bundle_size
    bundle_size=$(du -sh "$APP_BUNDLE" 2>/dev/null | cut -f1)
    ok "App bundle created: ${APP_BUNDLE} (${bundle_size})"
    echo ""
}

# ── Step 4: Create .dmg ────────────────────────────────────────────────────
step_dmg() {
    info "[4/5] Creating .dmg package..."
    local tmp_dmg="${BUILD_DIR}/tmp.dmg"
    local final_dmg="${DIST_DIR}/${DMG_NAME}"
    local vol_name="${APP_NAME} ${VERSION}"
    local mount_point="/Volumes/${APP_NAME}"

    # Ensure dist directory exists
    mkdir -p "$DIST_DIR"

    # Unmount if already mounted (from a previous run)
    if [[ -d "$mount_point" ]]; then
        hdiutil detach "$mount_point" -quiet -force 2>/dev/null || true
    fi

    # Calculate size based on app bundle + overhead
    local app_size_kb
    app_size_kb=$(du -sk "$STAGING_DIR" 2>/dev/null | cut -f1)
    if [[ -z "$app_size_kb" || "$app_size_kb" -lt 10000 ]]; then
        app_size_kb=50000
    fi
    local dmg_size_mb=$(( (app_size_kb / 1024) + 30 ))
    info "  App bundle size: ~$(( app_size_kb / 1024 )) MB, DMG size: ${dmg_size_mb} MB"

    # Create a temporary directory for DMG contents (with background icon)
    local dmg_contents="${BUILD_DIR}/dmg-contents"
    rm -rf "$dmg_contents"
    mkdir -p "$dmg_contents"

    # Copy app bundle into staging
    cp -R "$APP_BUNDLE" "$dmg_contents/"

    # Create /Applications symlink
    ln -sf /Applications "$dmg_contents/Applications"

    # Create temporary read-write DMG from folder
    info "  Creating temporary DMG..."
    # Remove old temp dmg if exists
    rm -f "$tmp_dmg"

    hdiutil create \
        -fs HFS+ \
        -volname "$vol_name" \
        -srcfolder "$dmg_contents" \
        -format UDRW \
        -nospotlight \
        "$tmp_dmg" \
        2>&1 | grep -E "^created:|^  " || true

    if [[ ! -f "$tmp_dmg" ]]; then
        fail "Failed to create temporary DMG."
    fi
    ok "Temporary DMG created"

    # Mount and customize layout
    info "  Customizing DMG layout..."
    hdiutil attach "$tmp_dmg" -mountpoint "$mount_point" -quiet 2>/dev/null

    # Set background color and icon positions via AppleScript
    osascript <<- APPLESCRIPT 2>/dev/null || true
tell application "Finder"
    set dmgWin to (every window whose name = "${vol_name}")
    if (count of dmgWin) > 0 then
        set the bounds of item 1 of dmgWin to {200, 100, 700, 432}
    end if
end tell
APPLESCRIPT

    # Wait for Finder to settle
    sleep 1

    # Set folder background color (lavender blue) using file system attributes
    # This is done via SetFile or by writing a custom .DS_Store
    # For simplicity we rely on the default clean HFS+ appearance

    # Detach
    hdiutil detach "$mount_point" -quiet -force 2>/dev/null || true
    sleep 1

    # Convert to compressed read-only DMG (UDZO with zlib compression)
    info "  Compressing final DMG..."
    rm -f "$final_dmg"
    hdiutil convert \
        "$tmp_dmg" \
        -format UDZO \
        -imagekey zlib-level=9 \
        -o "$final_dmg" \
        2>&1 | head -5

    # Clean up temp
    rm -f "$tmp_dmg"
    rm -rf "$dmg_contents"

    if [[ ! -f "$final_dmg" ]]; then
        fail "Failed to create final DMG at: $final_dmg"
    fi

    local dmg_size
    dmg_size=$(du -h "$final_dmg" 2>/dev/null | cut -f1)
    ok "DMG created: ${final_dmg} (${dmg_size})"
    echo ""
}

# ── Step 5: Cleanup ────────────────────────────────────────────────────────
step_cleanup() {
    info "[5/5] Cleaning up temporary build artifacts..."
    rm -rf "$STAGING_DIR"
    rm -rf "$ICONSET_DIR"
    rm -f  "${BUILD_DIR}/AppIcon.icns"
    rm -f  "${BUILD_DIR}/app-icon-1024.png"
    ok "Cleanup complete"
    echo ""
}

# ── Summary ────────────────────────────────────────────────────────────────
print_summary() {
    local final_dmg="${DIST_DIR}/${DMG_NAME}"

    echo "============================================"
    echo -e "  ${GREEN}Build Complete${RESET}"
    echo "============================================"
    echo ""
    echo "  Package: ${BOLD}${final_dmg}${RESET}"
    echo "  Version: ${VERSION}"
    if [[ -f "$final_dmg" ]]; then
        echo "  Size:    $(du -h "$final_dmg" 2>/dev/null | cut -f1)"
    fi
    echo ""
    echo "  Usage:"
    echo "    1. Open the .dmg file"
    echo "    2. Drag '${APP_NAME}.app' to Applications"
    echo "    3. Run: open -a '${APP_NAME}'"
    echo "    4. Open http://localhost:9999/admin"
    echo ""
    echo "  To codesign + notarize (future):"
    echo "    See packaging/macos/README.md"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────
main() {
    echo "============================================"
    echo "  ${APP_NAME} - macOS DMG Builder"
    echo "  Version ${VERSION}"
    echo "============================================"
    echo ""

    cd "$PROJECT_DIR"

    # Run steps in order
    check_prerequisites
    step_pyinstaller
    step_icon
    step_app_bundle
    step_dmg
    step_cleanup
    print_summary
}

main "$@"
