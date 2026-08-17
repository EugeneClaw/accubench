# effbench installer for Windows PowerShell
# Usage:   irm https://raw.githubusercontent.com/EugeneClaw/effbench/main/install.ps1 | iex
# Result:  $env:LOCALAPPDATA\effbench\bin\effbench.cmd on PATH.
$ErrorActionPreference = "Stop"

$Repo    = "https://github.com/EugeneClaw/effbench.git"
$Prefix  = if ($env:EFFBEN_PREFIX) { $env:EFFBEN_PREFIX } else { Join-Path $env:LOCALAPPDATA "effbench" }
$Bin     = Join-Path $Prefix "bin"
$Src     = Join-Path $Prefix "share\effbench"

Write-Host ""
Write-Host "  effbench installer"
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
  git pull --quiet
  Pop-Location
} else {
  Write-Host "  -> cloning repo..."
  if (Test-Path $Src) { Remove-Item -Recurse -Force $Src }
  git clone --depth 1 --quiet $Repo $Src
}

# 4. Launcher script.
$launcher = Join-Path $Bin "effbench.cmd"
@"
@echo off
REM effbench launcher
set EFFBEN_SRC=%LOCALAPPDATA%\effbench\share\effbench
"%EFFBEN_SRC%\..\..\python" "%EFFBEN_SRC%\effbench\__main__.py" %*
"@ | Out-File -Encoding ASCII $launcher

# Simpler: rely on python being on PATH.
@"
@echo off
set EFFBEN_SRC=%LOCALAPPDATA%\effbench\share\effbench
python "%EFFBEN_SRC%\effbench\__main__.py" %*
"@ | Out-File -Encoding ASCII $launcher

Write-Host "  OK installed: $launcher"

# 5. PATH hint.
$pathEnv = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($pathEnv -notlike "*$Bin*") {
  Write-Host ""
  Write-Host "  ! $Bin is not on your PATH."
  Write-Host "    Adding it now..."
  [Environment]::SetEnvironmentVariable("PATH", "$pathEnv;$Bin", "User")
  $env:PATH = "$env:PATH;$Bin"
  Write-Host "    (open a new terminal to pick it up)"
}

Write-Host ""
Write-Host "  next:"
Write-Host "    effbench setup    # finds your server, saves the URL"
Write-Host "    effbench go       # benchmark your server"
Write-Host ""
Write-Host "  done."