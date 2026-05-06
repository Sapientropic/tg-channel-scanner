#!/usr/bin/env bash
# Install tg-channel-scanner dependencies
# Requires: Python 3.12+

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== TG Channel Scanner Setup ==="

# Check Python version
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 12 ]; then
            PYTHON="$cmd"
            echo "Found Python $VER ($cmd)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.12+ required. Install from https://python.org"
    exit 1
fi

# Create venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
fi

source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

# Install tgcli
echo "Installing tgcli..."
pip install --upgrade pip --quiet
pip install pytgcli --quiet

# Check config
if [ ! -f "config.toml" ]; then
    cp config.example.toml config.toml
    echo ""
    echo "=== Next Steps ==="
    echo "1. Edit config.toml with your Telegram api_id and api_hash"
    echo "   Get them from: https://my.telegram.org/apps"
    echo "   (If the form shows ERROR, see docs/getting-api-credentials.md)"
    echo ""
    echo "2. Login:"
    echo "   tg auth login"
    echo ""
    echo "3. Run a scan:"
    echo "   ./scripts/scan.sh channel_lists/example.txt"
else
    echo "config.toml already exists, skipping."
fi

# Create output dir
mkdir -p output

echo "Setup complete."
