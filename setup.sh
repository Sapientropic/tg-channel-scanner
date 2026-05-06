#!/usr/bin/env bash
# Install tg-channel-scanner dependencies
# Requires: Python 3.12+ (system, or via uv/pipx)
#
# If your system Python is older than 3.12, install uv first:
#   https://docs.astral.sh/uv/getting-started/installation/
# setup.sh will then use uv to provision a managed Python automatically.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== TG Channel Scanner Setup ==="

# --- Find a suitable Python 3.12+ ---
# Skip Windows Store stubs (python3.exe that exits non-zero without printing a version).
find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            VER=$($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
            MAJOR=$(echo "$VER" | cut -d. -f1)
            MINOR=$(echo "$VER" | cut -d. -f2)
            if ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 12 ]) || [ "$MAJOR" -gt 3 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=""
USE_UV=false

if PYTHON=$(find_python); then
    VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "Found Python $VER ($PYTHON)"
elif command -v uv &>/dev/null; then
    echo "System Python < 3.12. Using uv to provision a managed Python..."
    USE_UV=true
else
    echo "Error: Python 3.12+ required." >&2
    echo "Install from https://python.org or install uv: https://docs.astral.sh/uv/" >&2
    exit 1
fi

# --- Create venv ---
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    if [ "$USE_UV" = true ]; then
        uv venv .venv --python 3.13
    else
        $PYTHON -m venv .venv
    fi
fi

# Activate and verify
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "Error: Failed to activate virtual environment."
    exit 1
fi

# --- Install dependencies ---
echo "Installing pinned core dependencies..."
if [ "$USE_UV" = true ]; then
    uv pip install -r requirements.txt
else
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
fi

echo "Installing optional pinned LLM dependencies (openai for summarize.py)..."
if [ "$USE_UV" = true ]; then
    uv pip install -r requirements-llm.txt 2>/dev/null || echo "  (openai not installed — summarize.py will need it later)"
else
    pip install -r requirements-llm.txt --quiet 2>/dev/null || echo "  (openai not installed — summarize.py will need it later)"
fi

TELETHON_VERSION="$(python -c "import telethon; print(telethon.__version__)" 2>/dev/null || true)"
if [ -z "$TELETHON_VERSION" ]; then
    echo "Error: telethon not importable. Check requirements.txt and venv." >&2
    exit 1
fi
echo "telethon $TELETHON_VERSION OK"

# --- Configure tgcli (writes to global config at ~/.config/tgcli/) ---
TGCLI_CONFIG_DIR="$HOME/.config/tgcli"
TGCLI_CONFIG="$TGCLI_CONFIG_DIR/config.toml"

if [ ! -f "$TGCLI_CONFIG" ]; then
    mkdir -p "$TGCLI_CONFIG_DIR"
    cp config.example.toml "$TGCLI_CONFIG"
    echo ""
    echo "=== Next Steps ==="
    echo "1. Edit Telegram API credentials:"
    echo "   $TGCLI_CONFIG"
    echo "   Get your api_id and api_hash from: https://my.telegram.org/apps"
    echo "   (If the form shows ERROR, see docs/getting-api-credentials.md)"
    echo ""
    echo "2. Run a scan (first run will prompt for login if no session):"
    echo "   source .venv/bin/activate"
    echo "   ./scripts/scan.sh channel_lists/example.txt"
else
    echo "tgcli config already exists at $TGCLI_CONFIG — skipping."
    echo "To reconfigure, edit: $TGCLI_CONFIG"
fi

# Make scripts executable (macOS/Linux)
chmod +x scripts/scan.sh 2>/dev/null || true

# Create output dir
mkdir -p output

echo ""
echo "Setup complete. Next: edit config and run a scan"
echo "  Config:  $TGCLI_CONFIG"
echo "  Scan:    source .venv/bin/activate && ./scripts/scan.sh channel_lists/example.txt"
