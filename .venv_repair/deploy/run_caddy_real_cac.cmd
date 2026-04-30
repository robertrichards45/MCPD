@echo off
cd /d "%~dp0"
if not exist "%~dp0cac-chain.pem" (
  echo Missing "%~dp0cac-chain.pem"
  echo Export the trusted DoD / federal issuing CA chain to PEM and place it there first.
  pause
  exit /b 1
)
if not exist "%~dp0..\app\.caddy" mkdir "%~dp0..\app\.caddy"
set "CADDY_HOME=%~dp0..\app\.caddy"
start "" powershell -NoProfile -Command "Start-Sleep -Seconds 3; Start-Process 'https://localhost'"
"C:\Users\rober\AppData\Local\Microsoft\WinGet\Packages\CaddyServer.Caddy_Microsoft.Winget.Source_8wekyb3d8bbwe\caddy.exe" run --config "%~dp0Caddyfile.local-cac-template"
