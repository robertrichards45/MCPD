@echo off
setlocal
cd /d "%~dp0"
set "DB_PATH=%~dp0data\app.db"
set "DB_PATH=%DB_PATH:\=/%"
set DATABASE_URL=sqlite:///%DB_PATH%
set APP_ENV=dev
set PREFERRED_URL_SCHEME=http
set TRUST_PROXY=0
set SESSION_COOKIE_SECURE=0
set REMEMBER_COOKIE_SECURE=0
set FORCE_HTTPS=0
set HSTS_ENABLED=0
set PORT=8092
set SSL_MODE=
set FLASK_DEBUG=0
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    "%VENV_PYTHON%" -B "%~dp0app.py"
    goto after_run
  )
)

if exist "%~dp0.deps314" (
  set "PYTHONPATH=%~dp0.deps314;%PYTHONPATH%"
  py -B "%~dp0app.py"
  goto after_run
)

echo.
echo No working project Python runtime was found.
pause
exit /b 1

:after_run
if errorlevel 1 (
  echo.
  echo Server exited with an error.
  pause
)
