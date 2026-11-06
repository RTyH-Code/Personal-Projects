@echo off
rem Starts a FireRed playtest run. Double-click, or drop a .gba ROM onto this file.
title FireRed Playtest
if not exist "%~dp0playtest.ps1" (
  echo The playtester isn't installed properly. Run Install.bat again.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0playtest.ps1" "%~1"
echo.
pause
