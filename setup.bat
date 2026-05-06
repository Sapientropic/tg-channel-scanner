@echo off
REM Install tg-channel-scanner dependencies (Windows)
REM Requires: Python 3.12+

cd /d "%~dp0"

echo === TG Channel Scanner Setup ===

python --version 2>nul || (
    echo Error: Python not found. Install from https://python.org
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing tgcli...
pip install --upgrade pip --quiet
pip install pytgcli --quiet

if not exist "config.toml" (
    copy config.example.toml config.toml
    echo.
    echo === Next Steps ===
    echo 1. Edit config.toml with your api_id and api_hash
    echo 2. Run: tg auth login
    echo 3. Run: scripts\scan.bat channel_lists\example.txt
) else (
    echo config.toml already exists.
)

if not exist "output" mkdir output

echo Setup complete.
