from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from scraper.config import load_db_config
from scraper.db import connect, ensure_schema, upsert_events
from scraper.runner import scrape_range


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Dakota Jazz events into MySQL")
    parser.add_argument("--start-month", required=True, help="Start month in YYYY-MM format")
    parser.add_argument("--end-month", required=True, help="End month in YYYY-MM format")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and print summary without DB writes")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _validate_month(args.start_month)
    _validate_month(args.end_month)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger("dakota-scraper")

    try:
        events = scrape_range(args.start_month, args.end_month, logger)
        if args.dry_run:
            logger.info("Dry run complete. %d row(s) parsed.", len(events))
            return 0
        db_config = load_db_config()
        with connect(db_config) as connection:
            ensure_schema(connection)
            count = upsert_events(connection, events)
        logger.info("Upsert complete. %d row(s) processed.", count)
        return 0
    except Exception:  # noqa: BLE001
        logger.exception("Scrape job failed")
        return 1


def _validate_month(value: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"Invalid month format '{value}'. Use YYYY-MM.") from exc


if __name__ == "__main__":
    sys.exit(main())

