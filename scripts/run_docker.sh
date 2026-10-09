
#!/usr/bin/env bash
set -euo pipefail

cd /srv/jobs/dakota-jazz-calendar

START_MONTH="$(date -u +%Y-%m)"
END_MONTH="$(date -u -d '+12 months' +%Y-%m)"

exec docker compose run --rm --no-deps \
  dakota-scraper \
  --start-month "$START_MONTH" \
  --end-month "$END_MONTH"
