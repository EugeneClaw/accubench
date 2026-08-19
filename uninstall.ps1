# AccuBench uninstaller for Windows PowerShell
# Usage: irm https://github.com/EugeneClaw/accubench/releases/latest/download/uninstall.ps1 | iex
# During the alias window (v0.9.23 → v1.0) this sweeps both command
# names and both data directories. After v1.0 only accubench remains.
$ErrorActionPreference = "Stop"

$Prefix  = if ($env:ACCUBENCH_PREFIX) { $env:ACCUBENCH_PREFIX } else { Join-Path $env:LOCALAPPDATA "accubench" }
$Bin     = Join-Path $Prefix "bin"
$Src     = Join-Path $Prefix "share\accubench"
$SrcOld  = Join-Path $Prefix "share\effbench"
$DataNew = Join-Path $env:USERPROFILE ".accubench"
$DataOld = Join-Path $env:USERPROFILE ".effbench"

Write-Host ""
Write-Host "  accubench uninstaller"
Write-Host "  ---------------------"
Write-Host ""

$removed = $false
foreach ($p in @((Join-Path $Bin "accubench.cmd"),
                 (Join-Path $Bin "effbench.cmd"),
                 $Bin, $Src, $SrcOld)) {
  if (Test-Path $p) {
    Remove-Item -Recurse -Force $p
    Write-Host "  OK removed $p"
    $removed = $true
  }
}

foreach ($d in @($DataNew, $DataOld)) {
  if (Test-Path $d) {
    $ans = Read-Host "  delete saved settings and reports ($d)? [y/N]"
    if ($ans -eq "y" -or $ans -eq "Y") {
      Remove-Item -Recurse -Force $d
      Write-Host "  OK removed $d"
    } else {
      Write-Host "  kept $d"
    }
  }
}

# Sweep Windows shortcuts on Desktop + Start Menu.
foreach ($home in @([Environment]::GetFolderPath("Desktop"),
                    (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"))) {
  $lnk = Join-Path $home "effbench.lnk"
  if (Test-Path $lnk) {
    Remove-Item -Force $lnk
    Write-Host "  OK removed $lnk"
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