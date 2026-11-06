# Starts a FireRed playtest run from Windows. Start it with Playtest.bat
# (or the "FireRed Playtest" desktop shortcut). You can drop a ROM onto it.

param([string]$Rom = '')

# Errors from programs are checked by hand ($LASTEXITCODE): in Windows PowerShell 5.1,
# 'Stop' turns any message a program prints to stderr into a fatal error.
$ErrorActionPreference = 'Continue'

function Fail($text) {
    Write-Host ''
    Write-Host $text -ForegroundColor Red
    exit 1
}
function To-Linux($path) {
    return (& wsl.exe -d $distro -e wslpath -a "$path" | Out-String).Trim()
}

$distroFile = Join-Path $PSScriptRoot 'distro.txt'
if (-not (Test-Path $distroFile)) { Fail 'The playtester is not installed yet. Run Install.bat first.' }
$distro = (Get-Content $distroFile -Raw).Trim()

Write-Host '=== FireRed Playtest ===' -ForegroundColor Green

# --- The ROM -------------------------------------------------------------------------------------
$Rom = $Rom.Trim('"')
if (-not $Rom) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = 'Choose your FireRed QoL + Hard ROM'
    $dialog.Filter = 'GBA ROM (*.gba)|*.gba|All files (*.*)|*.*'
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $Rom = $dialog.FileName
}
if (-not (Test-Path -LiteralPath $Rom)) { Fail "Can't find the ROM: $Rom" }
Write-Host "ROM: $Rom"

# --- How long, and which saves ---------------------------------------------------------------------
$hours = Read-Host 'How many hours should it play? (press Enter for 8)'
if (-not $hours) { $hours = '8' }
$parsed = 0.0
$hours = $hours.Replace(',', '.')
$ok = [double]::TryParse($hours, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)
if (-not $ok -or $parsed -le 0) { Fail "That isn't a number of hours: $hours" }

Write-Host ''
Write-Host 'Optional: a folder with your own .sav files, so it can also test later parts of the game.'
$saves = Read-Host 'Drag the folder into this window and press Enter (or just press Enter to skip)'
$saves = $saves.Trim().Trim('"')
$savesLinux = '-'  # "none" (Windows PowerShell drops empty arguments)
if ($saves) {
    if (-not (Test-Path -LiteralPath $saves -PathType Container)) { Fail "That isn't a folder: $saves" }
    $savesLinux = To-Linux $saves
}

Write-Host ''
Write-Host 'You can watch it play in your browser while it runs.'
$watchAnswer = Read-Host 'Have one game play at normal speed, so you can follow it? (y/N)'
$watch = '-'
if ($watchAnswer -match '^\s*y') { $watch = 'watch' }

# --- Run -----------------------------------------------------------------------------------------------
$name = 'playtest-' + (Get-Date -Format 'yyyyMMdd-HHmm')
$romLinux = To-Linux $Rom
$runs = (& wsl.exe -d $distro -e bash -c 'mkdir -p ~/firered-playtester/runs && wslpath -w ~/firered-playtester/runs' | Out-String).Trim()
if (-not $runs) { Fail 'The playtester is not installed in Ubuntu. Run Install.bat again.' }
$report = Join-Path (Join-Path $runs $name) 'report.html'
$live = Join-Path (Join-Path $runs $name) 'live.html'

# Keep Windows from going to sleep while this window is open (the run would pause).
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);'
[Win32.Power]::SetThreadExecutionState([uint32]2147483649) | Out-Null  # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x1)

Write-Host ''
Write-Host "Playing for $hours hour(s). Leave this window open; closing it stops the run." -ForegroundColor Yellow
Write-Host 'Your PC will stay awake until it finishes (the screen can still turn off).'
Write-Host "Watch it live (opens by itself in a moment): $live"
Write-Host "The report will be at: $report"
Write-Host '(It appears after about a minute and refreshes every 5 minutes.)'
Write-Host ''

# Open the live view as soon as the run has written it (a hidden helper waits for the file).
# (Its own variable is written `$n so this script doesn't fill it in. It gives up after 10 minutes.)
$opener = "`$n = 0; while (-not (Test-Path -LiteralPath '$live') -and `$n -lt 300) { Start-Sleep -Seconds 2; `$n++ }; " +
          "if (Test-Path -LiteralPath '$live') { Start-Process -FilePath '$live' }"
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-Command', $opener) | Out-Null

# No double quotes inside arguments here: Windows PowerShell 5.1 passes them on mangled.
& wsl.exe -d $distro --cd '~' -e bash firered-playtester/install/run.sh $romLinux $hours $savesLinux $name $watch
$code = $LASTEXITCODE
[Win32.Power]::SetThreadExecutionState([uint32]2147483648) | Out-Null  # back to normal

if (Test-Path -LiteralPath $report) {
    Write-Host ''
    Write-Host 'Finished. Opening the report...' -ForegroundColor Green
    Start-Process $report
} elseif ($code -ne 0) {
    Fail 'The playtest stopped with an error (see the messages above).'
}
