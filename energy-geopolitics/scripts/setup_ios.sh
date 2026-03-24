#!/bin/sh
# ============================================================
# Energy Geopolitics Intelligence Platform — iOS Setup
# Compatible with: iSH Shell (Alpine Linux) and a-Shell
# ============================================================
# Run once to install dependencies.
# Usage:  sh scripts/setup_ios.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ⚡ Energy Geopolitics Intelligence Platform"
echo "  iOS Setup Script"
echo ""

# ── Detect environment ────────────────────────────────────────
if [ -f /etc/alpine-release ]; then
    ENV="ish"
    echo "  Detected: iSH Shell (Alpine Linux)"
elif command -v python3 > /dev/null 2>&1; then
    ENV="ashell"
    echo "  Detected: a-Shell / generic iOS Python"
else
    echo "  ERROR: No Python environment detected."
    echo "  Install iSH from the App Store: https://ish.app"
    echo "  Or a-Shell: https://apps.apple.com/app/a-shell/id1473805438"
    exit 1
fi

echo ""

# ── iSH: install system packages ─────────────────────────────
if [ "$ENV" = "ish" ]; then
    echo "  [1/4] Updating Alpine package index..."
    apk update --quiet

    echo "  [2/4] Installing Python 3 and pip..."
    apk add --quiet python3 py3-pip

    echo "  [3/4] Installing Python packages..."
    pip3 install --quiet --no-cache-dir -r requirements-mobile.txt

    echo "  [4/4] Creating directories..."
    mkdir -p checkpoints

    echo ""
    echo "  Setup complete!"
    echo ""
    echo "  Start the server:  sh scripts/start.sh"
    echo "  Open in Safari:    http://localhost:8000"
    echo ""
    exit 0
fi

# ── a-Shell ───────────────────────────────────────────────────
echo "  [1/3] Checking Python version..."
python3 --version

echo "  [2/3] Installing Python packages..."
pip install --quiet --no-cache-dir -r requirements-mobile.txt 2>/dev/null \
  || pip3 install --quiet --no-cache-dir -r requirements-mobile.txt

echo "  [3/3] Creating directories..."
mkdir -p checkpoints

echo ""
echo "  Setup complete!"
echo ""
echo "  Start the server:  sh scripts/start.sh"
echo "  Open in Safari:    http://localhost:8000"
echo ""
