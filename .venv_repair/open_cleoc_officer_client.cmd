@echo off
cd /d "%~dp0"

if exist "%~dp0cleo_client.local.cmd" call "%~dp0cleo_client.local.cmd"
if "%CLEOC_CLIENT_URL%"=="" set "CLEOC_CLIENT_URL=http://%COMPUTERNAME%:8092/cleo/reports"

start "" "%CLEOC_CLIENT_URL%"
