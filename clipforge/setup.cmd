@echo off
rem Double-click me. Runs setup.ps1 without changing your PowerShell policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
echo.
pause
