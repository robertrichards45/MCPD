@echo off
cd /d "%~dp0"
set PORT=8092
set CLEOC_BIND=0.0.0.0
set CLEOC_OPEN_BROWSER=1
set FORCE_HTTPS=0
set HSTS_ENABLED=0
set TRUST_PROXY=0
set CAC_AUTH_ENABLED=0
set CAC_AUTO_REGISTER=0
set PUBLIC_SELF_REGISTER_ENABLED=0

echo.
echo CLEOC Shared Host
echo Host computer: %COMPUTERNAME%
echo Officers on the same network can connect to:
echo   http://%COMPUTERNAME%:%PORT%/cleo/reports
echo.

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Missing Python virtual environment at "%~dp0.venv".
  echo Create it first and install requirements.txt.
  pause
  exit /b 1
)

"%~dp0.venv\Scripts\python.exe" "%~dp0cleo_desktop.py"
