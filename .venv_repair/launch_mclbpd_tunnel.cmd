@echo off
cd /d "%~dp0"
set CLOUD_FLARED_BIN=C:\Program Files (x86)\cloudflared\cloudflared.exe
if exist "%~dp0tunnels.local.cmd" call "%~dp0tunnels.local.cmd"
if "%MCLBPD_TUNNEL_CONFIG%"=="" set "MCLBPD_TUNNEL_CONFIG=%~dp0deploy\cloudflared-mclbpd.yml"
if exist "%MCLBPD_TUNNEL_CONFIG%" (
  echo Using MCPD Cloudflare config "%MCLBPD_TUNNEL_CONFIG%".
  "%CLOUD_FLARED_BIN%" tunnel --config "%MCLBPD_TUNNEL_CONFIG%" run
  goto :after_run
)
if not "%MCLBPD_TUNNEL_TOKEN%"=="" (
  echo Using MCPD tunnel token from environment or tunnels.local.cmd.
  "%CLOUD_FLARED_BIN%" tunnel run --token "%MCLBPD_TUNNEL_TOKEN%" --url http://127.0.0.1:8091
  goto :after_run
)
echo.
echo MCPD remote access tunnel is not configured.
echo Do one of the following:
echo   1. Create "%~dp0deploy\cloudflared-mclbpd.yml" from the example and point it at http://127.0.0.1:8091
echo   2. Create "%~dp0tunnels.local.cmd" from tunnels.local.cmd.example and set MCLBPD_TUNNEL_TOKEN
pause
exit /b 1
:after_run
if errorlevel 1 (
  echo.
  echo Tunnel exited with an error.
  pause
)
