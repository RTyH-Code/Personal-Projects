@echo off
rem Starts a FireRed playtest run. Double-click, or drop a .gba ROM onto this file.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0playtest.ps1" "%~1"
