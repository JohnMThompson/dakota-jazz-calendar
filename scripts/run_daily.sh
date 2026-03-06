#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/john/git-repos/dakota-jazz-calendar"
LOG_DIR="$REPO_DIR/logs"
LOCK_FILE="$REPO_DIR/.daily_scrape.lock"

mkdir -p "$LOG_DIR"

if [[ -e "$LOCK_FILE" ]] && kill -0 "$(cat "$LOCK_FILE")" 2>/dev/null; then
  echo "$(date -Is) scraper already running (pid $(cat "$LOCK_FILE"))"
  exit 0
fi

echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

cd "$REPO_DIR"

# Load DB credentials from .env for non-interactive cron execution.
set -a
source "$REPO_DIR/.env"
set +a

START_MONTH="$(date +%Y-%m)"
END_MONTH="$(date -d '+1 month' +%Y-%m)"
LOG_FILE="$LOG_DIR/dakota_scrape_$(date +%F).log"

python3 -m scraper.cli --start-month "$START_MONTH" --end-month "$END_MONTH" >> "$LOG_FILE" 2>&1
