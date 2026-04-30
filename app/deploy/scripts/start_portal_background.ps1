$ErrorActionPreference = 'Stop'

$repoRoot = 'C:\Users\rober\Desktop\mcpd-portal'
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$appPy = Join-Path $repoRoot 'app.py'
$tmpDir = Join-Path $repoRoot 'tmp'
$stdoutLog = Join-Path $tmpDir 'portal-autostart.out.log'
$stderrLog = Join-Path $tmpDir 'portal-autostart.err.log'

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe"
}

if (-not (Test-Path $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
}

$listener = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
    Where-Object { $_.Port -eq 5055 } |
    Select-Object -First 1
if ($listener) {
    exit 0
}

$psi = @{
    FilePath = $pythonExe
    ArgumentList = @($appPy)
    WorkingDirectory = $repoRoot
    RedirectStandardOutput = $stdoutLog
    RedirectStandardError = $stderrLog
    WindowStyle = 'Hidden'
}

Start-Process @psi | Out-Null
