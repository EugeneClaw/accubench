# effbench uninstaller for Windows PowerShell
# Usage: irm https://raw.githubusercontent.com/EugeneClaw/effbench/main/uninstall.ps1 | iex
$ErrorActionPreference = "Stop"

$Prefix  = if ($env:EFFBEN_PREFIX) { $env:EFFBEN_PREFIX } else { Join-Path $env:LOCALAPPDATA "effbench" }
$Bin     = Join-Path $Prefix "bin"
$Src     = Join-Path $Prefix "share\effbench"
$Data    = Join-Path $env:USERPROFILE ".effbench"

Write-Host ""
Write-Host "  effbench uninstaller"
Write-Host "  --------------------"
Write-Host ""

$removed = $false
foreach ($p in @((Join-Path $Bin "effbench.cmd"), $Bin, $Src)) {
  if (Test-Path $p) {
    Remove-Item -Recurse -Force $p
    Write-Host "  OK removed $p"
    $removed = $true
  }
}

if (Test-Path $Data) {
  $ans = Read-Host "  delete saved settings and reports ($Data)? [y/N]"
  if ($ans -eq "y" -or $ans -eq "Y") {
    Remove-Item -Recurse -Force $Data
    Write-Host "  OK removed $Data"
  } else {
    Write-Host "  kept $Data"
  }
}

# Clean the PATH entry if present.
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -like "*$Bin*") {
  $cleaned = ($userPath -split ";" | Where-Object { $_ -ne $Bin -and $_ -ne "" }) -join ";"
  [Environment]::SetEnvironmentVariable("PATH", $cleaned, "User")
  Write-Host "  OK removed $Bin from PATH"
}

if (-not $removed) {
  Write-Host "  nothing to remove (not installed at $Prefix)"
}
Write-Host ""
Write-Host "  done."
