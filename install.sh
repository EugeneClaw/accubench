#!/usr/bin/env bash
# effbench one-line installer
# Usage:   curl -fsSL https://github.com/EugeneClaw/effbench/releases/latest/download/install.sh | bash
#          (release-asset URL — not raw.githubusercontent, which rate-limits (429) under load)
# Result:  /usr/local/bin/effbench ready to run, no Python venv needed.
set -euo pipefail

REPO="https://github.com/EugeneClaw/effbench.git"
PREFIX="${EFFBEN_PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin"
SRC="$PREFIX/share/effbench"

echo ""
echo "  effbench installer"
echo "  ───────────────────"
echo ""

# 1. Sanity check Python (3.9+).
if ! command -v python3 >/dev/null 2>&1; then
  echo "  ✗ python3 not found. Install Python 3.9 or newer first."
  echo "    macOS:   brew install python"
  echo "    Ubuntu:  sudo apt install python3"
  echo "    Windows: winget install Python.Python.3.12"
  exit 1
fi
PY_VER=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
PY_MAJOR=$(python3 -c 'import sys;print(sys.version_info[0])')
PY_MINOR=$(python3 -c 'import sys;print(sys.version_info[1])')
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
  echo "  ✗ Python $PY_VER found, need 3.9+."
  exit 1
fi
echo "  ✓ python3 $PY_VER"

# 2. Pick install location.
mkdir -p "$BIN" "$SRC"
echo "  → installing to $BIN and $SRC"

# 3. Clone or update the repo.
if [ -d "$SRC/.git" ]; then
  echo "  → updating existing install..."
  (cd "$SRC" && git pull --quiet)
else
  echo "  → cloning repo..."
  rm -rf "$SRC"
  git clone --depth 1 --quiet "$REPO" "$SRC"
fi

# 4. Write the launcher.
cat > "$BIN/effbench" <<EOF
#!/usr/bin/env bash
# effbench launcher — runs the python module from the install dir.
EFFBEN_SRC="$SRC"
export PYTHONPATH="\$EFFBEN_SRC\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m effbench "\$@"
EOF
chmod +x "$BIN/effbench"

echo "  ✓ installed: $BIN/effbench"

# 5. PATH hint if needed.
case ":$PATH:" in
  *":$BIN:"*)
    echo "  ✓ $BIN is already on your PATH" ;;
  *)
    echo ""
    echo "  ⚠ $BIN is not on your PATH."
    echo "    Add this to your ~/.zshrc or ~/.bashrc:"
    echo "      export PATH=\"$BIN:\$PATH\""
    echo "    Then restart the terminal (or: source ~/.zshrc)"
    echo "    Or run directly: $BIN/effbench"
    ;;
esac

echo ""
echo "  installed. starting effbench..."
echo ""
exec "$BIN/effbench"