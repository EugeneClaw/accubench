#!/usr/bin/env bash
# effbench uninstaller (Mac / Linux)
# Usage: curl -fsSL https://raw.githubusercontent.com/EugeneClaw/effbench/main/uninstall.sh | bash
set -u

DATA_DIR="$HOME/.effbench"
PREFIX="${EFFBEN_PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin/effbench"
SRC="$PREFIX/share/effbench"

echo ""
echo "  effbench uninstaller"
echo "  ────────────────────"
echo ""

removed=0
for p in "$BIN" "$SRC"; do
  if [ -e "$p" ]; then
    rm -rf "$p"
    echo "  ✓ removed $p"
    removed=1
  fi
done

if [ -d "$DATA_DIR" ]; then
  read -r -p "  delete saved settings and reports ($DATA_DIR)? [y/N]: " ans
  case "$ans" in
    y|Y) rm -rf "$DATA_DIR"; echo "  ✓ removed $DATA_DIR" ;;
    *)   echo "  · kept $DATA_DIR" ;;
  esac
fi

if [ "$removed" -eq 0 ]; then
  echo "  · nothing to remove (not installed at $PREFIX)"
fi
echo ""
echo "  done."
