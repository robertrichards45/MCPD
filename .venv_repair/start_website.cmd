@echo off
cd /d "%~dp0"
start "MCPD Portal Server" "%ComSpec%" /k "%~dp0launch_local.cmd"
start "Vet Assistance Tunnel" "%ComSpec%" /k "%~dp0launch_vet_tunnel.cmd"
start "MCPD Portal Tunnel" "%ComSpec%" /k "%~dp0launch_mclbpd_tunnel.cmd"
ping 127.0.0.1 -n 5 >nul
start "" "http://127.0.0.1:8091"
