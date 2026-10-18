@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "sfi_launch_exit=%errorlevel%"
if not "%sfi_launch_exit%"=="0" pause
exit /b %sfi_launch_exit%
