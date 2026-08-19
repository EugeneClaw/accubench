# AccuBench installer for Windows PowerShell
# Usage:   irm https://github.com/EugeneClaw/effbench/releases/latest/download/install.ps1 | iex
#          (release-asset URL — not raw.githubusercontent, which rate-limits (429) under load)
# Result:  $env:LOCALAPPDATA\effbench\bin\effbench.cmd on PATH.
$ErrorActionPreference = "Stop"

$Repo    = "https://github.com/EugeneClaw/effbench.git"
$Prefix  = if ($env:EFFBEN_PREFIX) { $env:EFFBEN_PREFIX } else { Join-Path $env:LOCALAPPDATA "effbench" }
$Bin     = Join-Path $Prefix "bin"
$Src     = Join-Path $Prefix "share\effbench"

Write-Host ""
Write-Host "  AccuBench installer"
Write-Host "  ------------------"
Write-Host ""

# 1. Python check.
$py = $null
foreach ($candidate in @("python", "python3", "py")) {
  $found = Get-Command $candidate -ErrorAction SilentlyContinue
  if ($found) { $py = $found.Source; break }
}
if (-not $py) {
  Write-Host "  X python not found. Install Python 3.9+ first:"
  Write-Host "    winget install Python.Python.3.12"
  exit 1
}
$ver = & $py -c "import sys;print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
$major = & $py -c "import sys;print(sys.version_info[0])"
$minor = & $py -c "import sys;print(sys.version_info[1])"
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 9)) {
  Write-Host "  X Python $ver found, need 3.9+."
  exit 1
}
Write-Host "  OK python $ver"

# 2. Make dirs.
New-Item -ItemType Directory -Path $Bin -Force | Out-Null
New-Item -ItemType Directory -Path $Src -Force | Out-Null
Write-Host "  -> installing to $Prefix"

# 3. Clone or update.
if (Test-Path (Join-Path $Src ".git")) {
  Write-Host "  -> updating existing install..."
  Push-Location $Src
  git fetch --quiet origin
  git reset --hard origin/main --quiet
  git clean -fdq
  Pop-Location
} else {
  Write-Host "  -> cloning repo..."
  if (Test-Path $Src) { Remove-Item -Recurse -Force $Src }
  git clone --depth 1 --quiet $Repo $Src
}

# 4. Launcher script — runs the module properly (relative imports work).
$launcher = Join-Path $Bin "effbench.cmd"
@"
@echo off
REM effbench launcher — UTF-8 mode so reports/labels never crash on cp1252.
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "EFFBEN_SRC=$Src"
set "PYTHONPATH=$Src;%PYTHONPATH%"
$py -m effbench %*
"@ | Out-File -Encoding ASCII $launcher

Write-Host "  OK installed: $launcher"

# 5. PATH.
$pathEnv = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($pathEnv -notlike "*$Bin*") {
  Write-Host ""
  Write-Host "  ! adding $Bin to your PATH..."
  [Environment]::SetEnvironmentVariable("PATH", "$pathEnv;$Bin", "User")
  $env:PATH = "$env:PATH;$Bin"
}

# 6. Desktop + Start Menu shortcuts ("effbench" — double-click to start,
#    close the window to stop; nothing runs in the background).
$uiLauncher = Join-Path $Bin "effbench-ui.cmd"
@"
@echo off
title effbench - close this window to stop
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "EFFBEN_SRC=$Src"
set "PYTHONPATH=$Src;%PYTHONPATH%"
$py -m effbench ui
pause
"@ | Out-File -Encoding ASCII $uiLauncher

$WshShell = New-Object -ComObject WScript.Shell
$Icon = Join-Path $Src "assets\accubench.ico"
foreach ($shortcutHome in @([Environment]::GetFolderPath("Desktop"),
                            (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"))) {
  $lnk = Join-Path $shortcutHome "effbench.lnk"
  $sc = $WshShell.CreateShortcut($lnk)
  $sc.TargetPath = $uiLauncher
  $sc.WorkingDirectory = $Bin
  if (Test-Path $Icon) { $sc.IconLocation = "$Icon,0" }
  $sc.Description = "AccuBench — local AI benchmark (close window to stop)"
  $sc.Save()
}
Write-Host "  OK shortcut: Desktop + Start Menu -> effbench"

Write-Host ""
Write-Host "  done. starting effbench..."
Write-Host ""
& $launcher