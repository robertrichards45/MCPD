@echo off
cd /d "%~dp0"
set CLOUD_FLARED_BIN=C:\Program Files (x86)\cloudflared\cloudflared.exe
if exist "%~dp0tunnels.local.cmd" call "%~dp0tunnels.local.cmd"
if "%VET_TUNNEL_TOKEN%"=="" (
  echo.
  echo Missing VET_TUNNEL_TOKEN.
  echo Create "%~dp0tunnels.local.cmd" from tunnels.local.cmd.example or set the variable in your shell.
  pause
  exit /b 1
)
"%CLOUD_FLARED_BIN%" tunnel run --token "%VET_TUNNEL_TOKEN%"
if errorlevel 1 (
  echo.
  echo Tunnel exited with an error.
  pause
)
