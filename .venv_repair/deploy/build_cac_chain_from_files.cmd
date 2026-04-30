@echo off
cd /d "%~dp0"
if "%~1"=="" (
  powershell -ExecutionPolicy Bypass -File "%~dp0scripts\build_cac_chain_from_files.ps1"
) else (
  powershell -ExecutionPolicy Bypass -File "%~dp0scripts\build_cac_chain_from_files.ps1" -SourceDir "%~1"
)
