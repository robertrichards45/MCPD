$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    throw "Missing virtual environment. Create .venv first."
}

& .\.venv\Scripts\python.exe -m pip install -r .\requirements-build.txt
& .\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm .\cleo_desktop.spec

$distRoot = Join-Path $PSScriptRoot 'dist\CLEOC Desktop'
if (-not (Test-Path $distRoot)) {
    throw "Build did not produce dist\CLEOC Desktop"
}

$readmePath = Join-Path $distRoot 'RUN_CLEOC_DESKTOP.txt'
@"
CLEOC Desktop Build

Run:
  CLEOC Desktop.exe

This packaged app stores its local database and uploaded files in:
  %LOCALAPPDATA%\MCPD-CLEOC-Desktop

Default local address:
  http://127.0.0.1:8092/cleo/reports

If you want a shared in-station host instead of a single-PC local app,
use the source project launcher:
  launch_cleoc_shared_host.cmd
"@ | Set-Content $readmePath

Write-Host "CLEOC Desktop build complete: $distRoot"
