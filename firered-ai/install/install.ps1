# Installs the FireRed playtester on Windows. Start it with Install.bat.
#
# 1. Makes sure WSL (Windows Subsystem for Linux) and Ubuntu are installed.
#    The first time, this needs administrator rights and a restart.
# 2. Installs Python inside Ubuntu.
# 3. Copies the playtester into Ubuntu and installs what it needs (setup.sh).
# 4. Puts two shortcuts on your desktop: "FireRed Playtest" (start a run;
#    you can drop a ROM on it) and "FireRed Playtest Reports" (past runs).
#
# Safe to run again: it picks up where it left off, and updates the
# playtester to the version in this folder.

param([switch]$Elevated)  # set when this script restarted itself with administrator rights

# Errors from programs are checked by hand ($LASTEXITCODE): in Windows PowerShell 5.1,
# 'Stop' turns any message a program prints to stderr into a fatal error.
$ErrorActionPreference = 'Continue'
$here = $PSScriptRoot
$source = (Resolve-Path (Join-Path $here '..')).Path

function Say($text) { Write-Host ''; Write-Host $text -ForegroundColor Cyan }
function Pause-IfOwnWindow {
    # Install.bat waits for a key itself; the administrator window has no Install.bat around it.
    if ($Elevated) { Write-Host ''; Read-Host 'Press Enter to close' | Out-Null }
}
function Fail($text) {
    Write-Host ''
    Write-Host $text -ForegroundColor Red
    Write-Host ''
    Write-Host "A log of this setup is in $log"
    Stop-Transcript | Out-Null
    Pause-IfOwnWindow
    exit 1
}
function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Get-UbuntuName {
    # "wsl -l -q" prints UTF-16, which shows up here with NUL characters between letters.
    $out = & wsl.exe -l -q 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    foreach ($line in $out) {
        $name = ($line -replace "`0", '').Trim()
        if ($name -like 'Ubuntu*') { return $name }
    }
    return $null
}

$log = Join-Path $env:TEMP 'FireRedPlaytester-install.log'
Start-Transcript -Path $log -Append | Out-Null
Write-Host '=== FireRed Playtester setup ===' -ForegroundColor Green
Write-Host "Installing from: $source"

# --- 1. WSL and Ubuntu ------------------------------------------------------------
$distro = Get-UbuntuName
if (-not $distro) {
    if (-not (Test-Admin)) {
        Say 'Ubuntu (WSL) is not installed yet. Installing it needs administrator permission.'
        Write-Host 'Windows will now ask "Do you want to allow this app to make changes to your device?". Click Yes.'
        try {
            Start-Process powershell.exe -Verb RunAs -ErrorAction Stop -ArgumentList @(
                '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Elevated')
        } catch {
            Fail 'Windows did not give administrator permission (maybe "No" was clicked). Run Install.bat again and click Yes.'
        }
        Write-Host ''
        Write-Host 'The setup continues in a NEW window (titled Administrator: Windows PowerShell).' -ForegroundColor Yellow
        Write-Host 'Follow the instructions there. If you do not see it, check the taskbar.' -ForegroundColor Yellow
        Stop-Transcript | Out-Null
        exit 0
    }
    Say 'Installing WSL and Ubuntu. This downloads about 1 GB and can take a while.'
    & wsl.exe --install -d Ubuntu
    if ($LASTEXITCODE -ne 0) {
        Fail ('Installing WSL failed. It needs Windows 10 version 2004 or later, or Windows 11, with ' +
              'virtualization turned on. See https://learn.microsoft.com/windows/wsl/install')
    }
    Write-Host ''
    Write-Host 'What happens next:' -ForegroundColor Yellow
    Write-Host '  1. If Windows asks you to restart, restart.'
    Write-Host '  2. An Ubuntu window opens (or open "Ubuntu" from the Start menu) and asks you'
    Write-Host '     to pick a username and password. They are only for Ubuntu; any will do.'
    Write-Host '     Nothing shows while you type the password - that is normal.'
    Write-Host '  3. When it shows a prompt ending in $, close that window and run Install.bat again.'
    Stop-Transcript | Out-Null
    Pause-IfOwnWindow
    exit 0
}
Say "Found $distro."

# Make sure Ubuntu's first-time setup (username and password) is done.
$user = (& wsl.exe -d $distro -e whoami 2>$null | Out-String).Trim()
if (-not $user) {
    Fail "Ubuntu didn't start. Open 'Ubuntu' from the Start menu once, finish its setup, then run Install.bat again."
}
if ($user -eq 'root') {
    Write-Host ''
    Write-Host 'Ubuntu has no user of your own yet. Open "Ubuntu" from the Start menu, follow its' -ForegroundColor Yellow
    Write-Host 'questions (username and password), then run Install.bat again.' -ForegroundColor Yellow
    Write-Host '(If you prefer, this works as root too: press Enter to carry on anyway.)'
    Read-Host 'Press Enter to continue' | Out-Null
}

# --- 2. Python inside Ubuntu -----------------------------------------------------------
Say 'Installing Python inside Ubuntu (needs an internet connection)...'
& wsl.exe -d $distro -u root -e bash -c 'export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip >/dev/null'
if ($LASTEXITCODE -ne 0) { Fail 'Installing Python inside Ubuntu failed. Check your internet connection and run Install.bat again.' }

# --- 3. The playtester ---------------------------------------------------------------------
$sourceLinux = (& wsl.exe -d $distro -e wslpath -a "$source" | Out-String).Trim()
if (-not $sourceLinux) { Fail "Couldn't find this folder from inside Ubuntu: $source" }
& wsl.exe -d $distro -e bash "$sourceLinux/install/setup.sh" "$sourceLinux"
if ($LASTEXITCODE -ne 0) { Fail 'Setting up the playtester failed (see the messages above).' }

# --- 4. Launchers and shortcuts ----------------------------------------------------------------
Say 'Adding shortcuts to your desktop...'
$app = Join-Path $env:LOCALAPPDATA 'FireRedPlaytester'
New-Item -ItemType Directory -Force -Path $app | Out-Null
Copy-Item -Force (Join-Path $here 'Playtest.bat') $app
Copy-Item -Force (Join-Path $here 'playtest.ps1') $app
Set-Content -Path (Join-Path $app 'distro.txt') -Value $distro -Encoding ASCII

$runs = (& wsl.exe -d $distro -e bash -c 'wslpath -w ~/firered-playtester/runs' | Out-String).Trim()
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $desktop 'FireRed Playtest.lnk'))
$lnk.TargetPath = Join-Path $app 'Playtest.bat'
$lnk.WorkingDirectory = $app
$lnk.Description = 'Start a FireRed playtest run (you can drop a ROM onto this)'
$lnk.Save()
if ($runs) {
    $lnk = $shell.CreateShortcut((Join-Path $desktop 'FireRed Playtest Reports.lnk'))
    $lnk.TargetPath = 'explorer.exe'
    $lnk.Arguments = "`"$runs`""
    $lnk.Description = 'Folders of past playtest runs; open report.html in one'
    $lnk.Save()
}

Write-Host ''
Write-Host 'All set!' -ForegroundColor Green
Write-Host 'Start a run: double-click "FireRed Playtest" on your desktop, or drop your ROM (.gba) onto it.'
Write-Host 'See results: "FireRed Playtest Reports" on your desktop, then report.html inside a run folder.'
Stop-Transcript | Out-Null
Pause-IfOwnWindow
