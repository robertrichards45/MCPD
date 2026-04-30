$ErrorActionPreference = 'Stop'

$repoRoot = 'C:\Users\rober\Desktop\mcpd-portal'
$starter = Join-Path $repoRoot 'deploy\scripts\start_portal_background.ps1'
$tmpDir = Join-Path $repoRoot 'tmp'
$logPath = Join-Path $tmpDir 'portal-watchdog.log'
$intervalSeconds = 15
$mutexName = 'Global\MCPDPortalWatchdog'

if (-not (Test-Path $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $logPath -Value "$timestamp $Message"
}

$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if (-not $createdNew) {
    Write-Log 'Portal watchdog already running; exiting duplicate launch'
    exit 0
}

Write-Log 'Portal watchdog started'

try {
    while ($true) {
        try {
            & $starter
        } catch {
            Write-Log "Starter failed: $($_.Exception.Message)"
        }

        Start-Sleep -Seconds $intervalSeconds
    }
} finally {
    if ($mutex) {
        $mutex.ReleaseMutex() | Out-Null
        $mutex.Dispose()
    }
}
