# ==============================================================================
# FixMate — Flask Application Launcher
# For VESIT Academic Demo — Yukta Karwa
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Launching FixMate Home Service Management Web App" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$baseDir = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $baseDir "venv\Scripts\python.exe"

if (-Not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Could not find virtual environment python at $venvPython" -ForegroundColor Red
    exit 1
}

# Check if MySQL port 3307 is active
$portCheck = Get-NetTCPConnection -LocalPort 3307 -ErrorAction SilentlyContinue
if (-Not $portCheck) {
    Write-Host "[WARNING] MySQL does not appear to be listening on port 3307." -ForegroundColor Yellow
    Write-Host "Please run .\scripts\start_mysql.ps1 in a separate terminal first." -ForegroundColor Yellow
}

Set-Location $baseDir
Write-Host "[FixMate] Starting Flask server at http://127.0.0.1:5000 ..." -ForegroundColor Green
& $venvPython run.py

