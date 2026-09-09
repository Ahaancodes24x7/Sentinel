# =============================================================================
# Sentinel — share the running console over a Microsoft Dev Tunnel.
#
#   .\share.ps1              # build, start, tunnel
#   .\share.ps1 -SkipBuild   # reuse the existing frontend/dist
#
# The API process serves the built console as well as the JSON API, so the whole
# system is ONE origin behind ONE port. The frontend calls a relative /api/v1,
# which means it resolves against whatever host the visitor lands on — the dev
# tunnel URL, a LAN address, localhost — with no rebuild and no CORS.
#
# BEFORE FIRST USE, once per machine:
#     devtunnel user login
#
# SECURITY: -a / --allow-anonymous makes this reachable by anyone with the link.
# That is the point when sharing a demo, but be aware of what is behind it:
#   * the three demo logins are hardcoded (manager_demo / hse_demo /
#     auditor_demo, all "demo123"), so the link IS the credential
#   * a manager login can trigger the clustering job and ingest reports
#   * the data is the synthetic corpus, not real OIL data
# Stop the tunnel (Ctrl+C) when you are done sharing.
# =============================================================================

param(
    [int]$Port = 8000,
    [string]$Database = "sqlite:///./scratch_demo.db",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$devtunnel = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\devtunnel.exe"
if (-not (Test-Path $devtunnel)) {
    $cmd = Get-Command devtunnel -ErrorAction SilentlyContinue
    if ($cmd) { $devtunnel = $cmd.Source }
    else { throw "devtunnel not found. Install it with:  winget install Microsoft.devtunnel" }
}

# --- 1. build the console -----------------------------------------------------
if (-not $SkipBuild) {
    Write-Host "[1/4] Building the console..." -ForegroundColor Cyan
    Push-Location (Join-Path $root "frontend")
    try { npm run build } finally { Pop-Location }
} else {
    Write-Host "[1/4] Skipping build (-SkipBuild)" -ForegroundColor DarkGray
}

if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
    throw "frontend/dist not found. Run without -SkipBuild first."
}

# --- 2. free the port ---------------------------------------------------------
Write-Host "[2/4] Freeing port $Port..." -ForegroundColor Cyan
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    $conns | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

# --- 3. start the unified server ---------------------------------------------
Write-Host "[3/4] Starting Sentinel on port $Port..." -ForegroundColor Cyan
$env:DATABASE_URL = $Database
if ($Database -like "sqlite*") { $env:TEST_ISOLATED_SQLITE = "1" }
$env:PYTHONPATH = "$(Join-Path $root 'aiml\src');$root"

$server = Start-Process -FilePath "python" `
    -ArgumentList @("-W", "ignore", "-m", "uvicorn", "backend.main:app",
                    "--port", "$Port", "--host", "127.0.0.1") `
    -WorkingDirectory $root -PassThru -WindowStyle Hidden

# Wait for it to answer rather than guessing with a sleep.
$ready = $false
foreach ($i in 1..40) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/v1/health" -TimeoutSec 3 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}
if (-not $ready) {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    throw "Server did not become healthy on port $Port."
}
Write-Host "      Server healthy (PID $($server.Id))" -ForegroundColor Green

# --- 4. open the tunnel -------------------------------------------------------
Write-Host "[4/4] Opening dev tunnel (anonymous access)..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Share the https://...devtunnels.ms link printed below." -ForegroundColor Yellow
Write-Host "  Demo logins: manager_demo / hse_demo / auditor_demo  (password: demo123)" -ForegroundColor Yellow
Write-Host "  Ctrl+C stops the tunnel; the server keeps running on PID $($server.Id)." -ForegroundColor DarkGray
Write-Host ""

try {
    & $devtunnel host -p $Port -a --protocol https
} finally {
    Write-Host ""
    Write-Host "Tunnel closed. Stopping the server..." -ForegroundColor DarkGray
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
