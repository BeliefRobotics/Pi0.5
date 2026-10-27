@echo off
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows.ps1" -Action Stop
set "PI05_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %PI05_EXIT%
