# macOS DMG Packaging — AI Privacy Gateway

This directory contains scripts and configuration files for building a
standalone macOS `.dmg` installer for AI Privacy Gateway.

## Prerequisites

- **macOS 11.0 (Big Sur)** or later
- **Xcode Command Line Tools** (`xcode-select --install`)
- **Python 3.10 or later** (from [python.org](https://www.python.org/downloads/) or Homebrew)
- **PyInstaller** (`pip3 install pyinstaller`)

## Quick Start

```bash
# From the project root directory:
bash packaging/macos/build_dmg.sh
```

The script will:

1. Install Python dependencies (`requirements.txt`)
2. Build a standalone executable with PyInstaller
3. Generate a custom application icon
4. Create a proper `.app` bundle with `Info.plist`
5. Package everything into a compressed `.dmg` file

**Output:** `dist/AI-Privacy-Gateway-2.0.0.dmg`

## Installation by Users

1. Open the `.dmg` file
2. Drag `AI Privacy Gateway.app` into the `Applications` folder
3. Launch from Applications (a terminal window will appear — this is normal)
4. Open `http://localhost:9999/admin` in a browser

## Script Details

| File | Purpose |
|------|---------|
| `build_dmg.sh` | Main build script — runs PyInstaller, creates `.app`, builds `.dmg` |
| `entitlements.plist` | Hardened Runtime entitlements for code signing (future use) |
| `README.md` | This file |

## Code Signing and Notarization

Code signing is optional but recommended for distribution. The entitlements
file is ready for use. To sign and notarize, create a `codesign.sh` script
(replace placeholders with your Apple credentials):

```bash
# Set up signing identity and notary credentials
APPLE_ID="your@apple.id"
APP_PASSWORD="@keychain:AC_PASSWORD"  # App-specific password in keychain
TEAM_ID="YOUR_TEAM_ID"
BUNDLE_ID="com.aiprivacygateway.app"

# Sign the .app bundle
codesign --deep --force --verify --verbose \
    --sign "Developer ID Application: Your Name (${TEAM_ID})" \
    --options runtime \
    --entitlements packaging/macos/entitlements.plist \
    "dist/AI Privacy Gateway.app"

# Submit for notarization
xcrun notarytool submit "dist/AI-Privacy-Gateway-2.0.0.dmg" \
    --apple-id "${APPLE_ID}" \
    --password "${APP_PASSWORD}" \
    --team-id "${TEAM_ID}" \
    --wait

# Staple the ticket
xcrun stapler staple "dist/AI-Privacy-Gateway-2.0.0.dmg"
```

## File Structure of the `.app` Bundle

```
AI Privacy Gateway.app/
└── Contents/
    ├── Info.plist          # Bundle metadata
    ├── MacOS/
    │   └── AI Privacy Gateway   # PyInstaller-built executable
    ├── Resources/
    │   └── app.icns       # Application icon
    └── PkgInfo            # Type code (APPL)
```

## Notes

- The app runs as a **background service** (`LSUIElement = true`). No Dock icon
  will appear — use the browser at `http://localhost:9999/admin` to interact.
- The `.dmg` uses HFS+ filesystem with zlib compression for broad compatibility.
- The icon is generated at build time using Python (standard library only) and
  does not require any external image tools.
