@echo off
rem Installs the FireRed playtester. Double-click this file.
title FireRed Playtester setup
if not exist "%~dp0install.ps1" goto notextracted
if not exist "%~dp0setup.sh" goto notextracted
if not exist "%~dp0..\playtest.py" goto moved
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
echo This window can be closed now. (A log of the setup is in %TEMP%\FireRedPlaytester-install.log)
pause
exit /b

:moved
echo.
echo  The install folder has been moved out of the firered-ai folder.
echo  It needs to stay inside it: the installer copies the playtester from the folder around it.
echo  Please:
echo    1. Close this window.
echo    2. Right-click the downloaded ZIP file, choose "Extract All...", then "Extract".
echo    3. In the extracted folder, open firered-ai, then install, and double-click Install.bat there.
echo.
pause
exit /b 1

:notextracted
echo.
echo  The installer's other files aren't next to Install.bat.
echo.
echo  This happens when Install.bat is opened from inside the ZIP file.
echo  Please:
echo    1. Close this window.
echo    2. Right-click the downloaded ZIP file and choose "Extract All...", then "Extract".
echo    3. In the extracted folder, open firered-ai, then install,
echo       and double-click Install.bat there.
echo.
pause
exit /b 1
