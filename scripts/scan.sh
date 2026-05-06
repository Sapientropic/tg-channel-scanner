#!/usr/bin/env bash
# Batch-read Telegram channels and save messages as JSONL
# Usage: ./scan.sh <channel_list.txt> [hours]
# Example: ./scan.sh channel_lists/job-search.txt 24

set -euo pipefail

LIST="${1:?Usage: scan.sh <channel_list.txt> [hours]}"
HOURS="${2:-24}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Validate input
if [ ! -f "$LIST" ]; then
    echo "Error: Channel list not found: $LIST" >&2
    exit 1
fi

# Activate venv
source "$SCRIPT_DIR/.venv/bin/activate" 2>/dev/null || source "$SCRIPT_DIR/.venv/Scripts/activate" 2>/dev/null
if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "Error: venv not activated. Run setup.sh first." >&2
    exit 1
fi

if ! command -v tg &>/dev/null; then
    echo "Error: tg command not found. Run setup.sh first." >&2
    exit 1
fi

# Calculate after date (cross-platform)
if date -v-${HOURS}H +%Y-%m-%d &>/dev/null; then
    AFTER=$(date -v-${HOURS}H +%Y-%m-%d)
elif command -v gdate &>/dev/null && gdate -d "-${HOURS} hours" +%Y-%m-%d &>/dev/null; then
    AFTER=$(gdate -d "-${HOURS} hours" +%Y-%m-%d)
elif date -d "-${HOURS} hours" +%Y-%m-%d &>/dev/null; then
    AFTER=$(date -d "-${HOURS} hours" +%Y-%m-%d)
else
    AFTER=$(python -c "from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=${HOURS})).strftime('%Y-%m-%d'))")
fi

# Output files
mkdir -p "$SCRIPT_DIR/output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT="$SCRIPT_DIR/output/scan_${TIMESTAMP}.jsonl"
ERRORS="$SCRIPT_DIR/output/scan_${TIMESTAMP}.errors.log"

echo "Scan started: $(date)"
echo "Time window: past ${HOURS}h (since $AFTER)"
echo "Channel list: $LIST"
echo "Output: $OUTPUT"
echo "---"

CHANNELS=0
FAILURES=0
while IFS= read -r ch; do
    [ -z "$ch" ] && continue
    [[ "$ch" == \#* ]] && continue
    CHANNELS=$((CHANNELS + 1))
    echo "[$CHANNELS] Reading: $ch"

    if ! tg read "$ch" --after "$AFTER" --limit 100 >> "$OUTPUT" 2>>"$ERRORS"; then
        echo "  ⚠ Failed: $ch (see $(basename "$ERRORS"))" >&2
        FAILURES=$((FAILURES + 1))
    fi
    sleep "${SCAN_DELAY:-1}"
done < "$LIST"

COUNT=$(wc -l < "$OUTPUT" 2>/dev/null | tr -d ' ')

echo "---"
echo "Done. $CHANNELS channels scanned, $COUNT messages collected."
if [ "$FAILURES" -gt 0 ]; then
    echo "⚠ $FAILURES channels failed. See: $(basename "$ERRORS")"
fi
echo "Output: $OUTPUT"
echo ""
echo "Next: Summarize with your preferred AI:"
echo "  OpenAI/DeepSeek: python scripts/summarize.py --input $OUTPUT --profile profiles/YOUR_PROFILE.md"
echo "  Codex/Claude:    Point your agent at $OUTPUT + profiles/YOUR_PROFILE.md"
