$ErrorActionPreference = 'SilentlyContinue'

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$dbPath = Join-Path $repoRoot 'data\app.db'

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

Write-Host "MCPD Portal Resume Check" -ForegroundColor Green
Write-Host "Repo: $repoRoot"

Write-Section "Web Server"
$listener = netstat -ano | Select-String ':8091'
if ($listener) {
    $listener | ForEach-Object { $_.Line }
} else {
    Write-Host "Port 8091 is not listening."
    Write-Host "Start it with: .\launch_local.cmd"
}

Write-Section "CAC Detection"
certutil -scinfo

Write-Section "Config"
if (Test-Path $envPath) {
    Get-Content $envPath |
        Select-String '^(APP_ENV|APP_DOMAIN|TRUST_PROXY|CAC_AUTH_ENABLED|CAC_AUTO_REGISTER|CAC_DEBUG_ENABLED|CAC_USERNAME_HEADERS|CAC_NAME_HEADERS)=' |
        ForEach-Object { $_.Line }
} else {
    Write-Host ".env not found"
}

Write-Section "CAC User Check"
if (Test-Path $dbPath) {
    @"
import sqlite3
conn = sqlite3.connect(r'$dbPath')
cur = conn.cursor()
rows = list(cur.execute("select id, username, active from user order by id"))
for row in rows:
    print(row)
conn.close()
"@ | py -
} else {
    Write-Host "Database not found at $dbPath"
}

Write-Section "Next Step"
Write-Host "If certutil still shows SCARD_STATE_EMPTY, this PC still cannot detect the CAC."
Write-Host "Use another government PC with working CAC detection, or continue with username/password on this one."
