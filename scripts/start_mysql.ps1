# ==============================================================================
# FixMate — Dedicated MySQL Server Starter (Port 3307)
# For VESIT Academic Demo — Yukta Karwa
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting FixMate Dedicated MySQL 26.7 Server on Port 3307" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$baseDir = Split-Path -Parent $PSScriptRoot
$iniPath = Join-Path $baseDir "var\my_fixmate.ini"
$mysqlExe = "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysqld.exe"

if (-Not (Test-Path $mysqlExe)) {
    Write-Host "[ERROR] Could not find mysqld.exe at $mysqlExe" -ForegroundColor Red
    exit 1
}

# Test if port 3307 is already listening
$portCheck = Get-NetTCPConnection -LocalPort 3307 -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "[FixMate] Dedicated MySQL Server is ALREADY RUNNING on port 3307." -ForegroundColor Green
    exit 0
}

Write-Host "[FixMate] Launching mysqld with defaults-file: $iniPath ..." -ForegroundColor Yellow
& $mysqlExe --defaults-file="$iniPath" --console

