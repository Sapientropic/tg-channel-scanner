#!/usr/bin/env bash
# Batch-read Telegram channels and save messages as JSONL
# Usage: ./scan.sh <channel_list.txt> [hours]
# Example: ./scan.sh channel_lists/job-search.txt 24

set -e

LIST="${1:?Usage: scan.sh <channel_list.txt> [hours]}"
HOURS="${2:-24}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Activate venv
source "$SCRIPT_DIR/.venv/bin/activate" 2>/dev/null || source "$SCRIPT_DIR/.venv/Scripts/activate" 2>/dev/null

# Calculate after date (cross-platform)
if date -v-${HOURS}H +%Y-%m-%d &>/dev/null; then
    AFTER=$(date -v-${HOURS}H +%Y-%m-%d)
elif date -d "-${HOURS} hours" +%Y-%m-%d &>/dev/null; then
    AFTER=$(date -d "-${HOURS} hours" +%Y-%m-%d)
else
    AFTER=$(python -c "from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=${HOURS})).strftime('%Y-%m-%d'))")
fi

# Output file
mkdir -p "$SCRIPT_DIR/output"
TIMESTAMP=$(date +%Y%m%d_%H%M)
OUTPUT="$SCRIPT_DIR/output/scan_${TIMESTAMP}.jsonl"

echo "Scan started: $(date)"
echo "Time window: past ${HOURS}h (since $AFTER)"
echo "Channel list: $LIST"
echo "Output: $OUTPUT"
echo "---"

COUNT=0
CHANNELS=0
while IFS= read -r ch; do
    [ -z "$ch" ] && continue
    [[ "$ch" == \#* ]] && continue
    CHANNELS=$((CHANNELS + 1))
    echo "[$CHANNELS] Reading: $ch"

    tg read "$ch" --after "$AFTER" --limit 100 >> "$OUTPUT" 2>&1 || true
    sleep 1
done < "$LIST"

COUNT=$(grep -c '"id"' "$OUTPUT" 2>/dev/null || echo 0)

echo "---"
echo "Done. $CHANNELS channels scanned, $COUNT messages collected."
echo "Output: $OUTPUT"
echo ""
echo "Next: Summarize with your preferred AI:"
echo "  DeepSeek: deepseek exec --auto \"Read $OUTPUT, filter using profile in profiles/YOUR_PROFILE.md\""
echo "  Codex:    Point your agent at $OUTPUT + profiles/YOUR_PROFILE.md"
