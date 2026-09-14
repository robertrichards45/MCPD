@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==============================================
echo MCPD Portal - Safe Source Update

echo Repository: %CD%
echo ==============================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git is not available in PATH.
  pause
  exit /b 1
)

for /f "delims=" %%G in ('git status --porcelain') do (
  echo ERROR: Local uncommitted changes were found.
  echo This updater will not overwrite local work.
  echo.
  git status --short
  pause
  exit /b 1
)

echo [1/3] Fetching current main branch...
git fetch origin main
if errorlevel 1 goto :gitfail

echo [2/3] Switching to main...
git checkout main
if errorlevel 1 goto :gitfail

echo [3/3] Fast-forwarding to origin/main...
git pull --ff-only origin main
if errorlevel 1 goto :gitfail

echo.
echo Current source commit:
git rev-parse --short HEAD
echo.
echo SOURCE UPDATE COMPLETE.
echo.
echo IMPORTANT:
echo 1. Close the existing "MCPD Portal Server" command window.
echo 2. Re-run launch_local.cmd to start the updated portal on port 8091.
echo 3. Leave the Cloudflare tunnel running if it is already connected.
echo 4. Refresh mclbpd.com after the local server restarts.
echo.
pause
exit /b 0

:gitfail
echo.
echo ERROR: Git update failed. No source files were overwritten by this helper.
pause
exit /b 1
