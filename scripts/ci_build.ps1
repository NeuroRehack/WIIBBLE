# Shared Windows CI/local build script for WIIBBLE.
# Version: WIIBBLE_VERSION env var, or pyproject.toml via scripts/get_version.py

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

if (-not $env:WIIBBLE_VERSION) {
    $env:WIIBBLE_VERSION = uv run python scripts/get_version.py
}
Write-Host "[ci_build] Version: $($env:WIIBBLE_VERSION)"
if (-not $env:WIIBBLE_PROFILE) {
    $env:WIIBBLE_PROFILE = "full"
}
Write-Host "[ci_build] Profile: $($env:WIIBBLE_PROFILE)"

Write-Host "[ci_build] Installing dependencies..."
uv sync --extra dev --extra analysis --extra thrive
uv pip install -e .

$env:CI = "true"
.\compiler.bat
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$distDir = "dist_nuitka\wiibble.dist"
if (-not (Test-Path $distDir)) {
    throw "Expected Nuitka output at $distDir"
}

Write-Host "[ci_build] Verifying dist layout..."
# Same interpreter compiler.bat used: `uv run` would re-sync and could drop extras.
.\.venv\Scripts\python.exe scripts\verify_dist_layout.py --dist-dir $distDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$zipSuffix = ""
if ($env:WIIBBLE_PROFILE -and $env:WIIBBLE_PROFILE -ne "full") {
    $zipSuffix = "-$($env:WIIBBLE_PROFILE)"
}
$zipName = "WIIBBLE-$($env:WIIBBLE_VERSION)$zipSuffix-portable.zip"
Write-Host "[ci_build] Creating portable archive: $zipName"
if (Test-Path $zipName) { Remove-Item $zipName }
Compress-Archive -Path "$distDir\*" -DestinationPath $zipName

$installer = Get-ChildItem -Path "installer_output" -Filter "WIIBBLE-*-Setup.exe" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($installer) {
    Write-Host "[ci_build] Installer: $($installer.FullName)"
} else {
    Write-Host "[ci_build] No installer found (iscc may be missing)."
}

Write-Host "[ci_build] Done."
