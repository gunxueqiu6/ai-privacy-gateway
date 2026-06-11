# AI Privacy Gateway — Chrome Extension Packaging Script
# Usage: powershell -ExecutionPolicy Bypass -File package.ps1

$ErrorActionPreference = "Stop"
$extDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDir = Join-Path $extDir "dist"
$zipPath = Join-Path $outDir "ai-privacy-gateway-extension.zip"
$stagingDir = Join-Path $outDir "staging"

# Files to include in the package
$files = @(
    "manifest.json",
    "background.js",
    "content.js",
    "content.css",
    "popup.html",
    "popup.js",
    "options.html",
    "options.js",
    "icons/icon16.png",
    "icons/icon48.png",
    "icons/icon128.png"
)

# Clean up
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }

# Create staging directory
New-Item -ItemType Directory -Path $stagingDir | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stagingDir "icons") | Out-Null

Write-Host "Packaging extension..." -ForegroundColor Cyan

# Verify all files exist and copy to staging
$missing = @()
foreach ($file in $files) {
    $srcPath = Join-Path $extDir $file
    $dstPath = Join-Path $stagingDir $file
    if (-not (Test-Path $srcPath)) {
        $missing += $file
    } else {
        Copy-Item $srcPath $dstPath
        Write-Host "  Added: $file" -ForegroundColor Gray
    }
}

if ($missing.Count -gt 0) {
    Write-Host "ERROR: Missing files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

# Create zip
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -Force

# Clean up staging
Remove-Item $stagingDir -Recurse -Force

$zipSize = (Get-Item $zipPath).Length
$zipSizeKB = [math]::Round($zipSize / 1KB, 1)

Write-Host ""
Write-Host "Package created: $zipPath" -ForegroundColor Green
Write-Host "Size: $zipSizeKB KB" -ForegroundColor Green
Write-Host ""
Write-Host "Ready for Chrome Web Store submission!" -ForegroundColor Yellow
Write-Host "Upload at: https://chrome.google.com/webstore/devconsole" -ForegroundColor Yellow
