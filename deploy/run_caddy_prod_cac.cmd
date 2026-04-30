@echo off
cd /d "%~dp0"
if not exist "C:\certs\cac-chain.pem" (
  echo Missing C:\certs\cac-chain.pem
  echo Place the trusted DoD/Federal CAC issuer chain PEM at that path.
  pause
  exit /b 1
)
"C:\Users\rober\AppData\Local\Microsoft\WinGet\Packages\CaddyServer.Caddy_Microsoft.Winget.Source_8wekyb3d8bbwe\caddy.exe" run --config "%~dp0Caddyfile.example"
