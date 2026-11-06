@echo off
rem Installs the FireRed playtester. Double-click this file.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 pause
