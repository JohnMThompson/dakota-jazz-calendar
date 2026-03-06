# dakota-jazz-calendar

Scrapes the Dakota event calendar and upserts event rows into MySQL.

## Captured Fields

- `event_date`
- `event_time` (string, e.g. `6:00 PM, 8:30 PM`)
- `performer_name`
- `genre`
- `description_short` (first paragraph)
- `source_url`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Create `.env`:

```bash
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=dakota
DB_USER=your_user
DB_PASSWORD=your_password
```

## Run

Dry run (no DB writes):

```bash
dakota-scraper --start-month 2026-03 --end-month 2027-02 --dry-run
```

Load into DB:

```bash
dakota-scraper --start-month 2026-03 --end-month 2027-02
```

## Scheduling (cron)

Example monthly run at 2:15 AM on the first day of each month:

```cron
15 2 1 * * cd /home/john/git-repos/dakota-jazz-calendar && /home/john/git-repos/dakota-jazz-calendar/.venv/bin/dakota-scraper --start-month $(date +\%Y-\%m) --end-month $(date -d '+1 month' +\%Y-\%m)
```

## Notes

- Table schema is in `schema.sql`.
- Unique key is `(event_date, event_time, performer_name)` for idempotent upserts.
