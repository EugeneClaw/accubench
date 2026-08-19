#!/usr/bin/env bash
# AccuBench uninstaller (Mac / Linux)
# Usage: curl -fsSL https://github.com/EugeneClaw/accubench/releases/latest/download/uninstall.sh | bash
# During the alias window (v0.9.23 → v1.0) this sweeps both command
# names and both data directories. After v1.0 only accubench remains.
set -u

DATA_DIRS=("$HOME/.accubench" "$HOME/.effbench")
PREFIX="${ACCUBENCH_PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
SRC_DIR="$PREFIX/share/accubench"
SRC_OLD="$PREFIX/share/effbench"

echo ""
echo "  accubench uninstaller"
echo "  ──────────────────────"
echo ""

removed=0
for p in \
    "$BIN_DIR/accubench" "$BIN_DIR/accubench.cmd" \
    "$BIN_DIR/effbench" "$BIN_DIR/effbench.cmd" \
    "$BIN_DIR" \
    "$SRC_DIR" "$SRC_OLD" \
    "$HOME/Applications/effbench.app" \
    "$HOME/.local/share/applications/effbench.desktop"
do
  if [ -e "$p" ]; then
    rm -rf "$p"
    echo "  ✓ removed $p"
    removed=1
  fi
done

for d in "${DATA_DIRS[@]}"; do
  if [ -d "$d" ]; then
    read -r -p "  delete saved settings and reports ($d)? [y/N]: " ans
    case "$ans" in
      y|Y) rm -rf "$d"; echo "  ✓ removed $d" ;;
      *)   echo "  · kept $d" ;;
    esac
  fi
done

# Remove user-level Start Menu + Desktop shortcuts (Windows-shim support
# on Mac/Linux dev boxes). Best-effort; missing dirs are silent.
for d in "$HOME/Desktop" "$HOME/.local/share/applications"; do
  [ -f "$d/effbench.lnk" ] && rm -f "$d/effbench.lnk" && echo "  ✓ removed $d/effbench.lnk"
  [ -f "$d/effbench.desktop" ] && rm -f "$d/effbench.desktop" && echo "  ✓ removed $d/effbench.desktop"
done

if [ "$removed" -eq 0 ]; then
  echo "  · nothing to remove (not installed at $PREFIX)"
fi
echo ""
echo "  done."