from __future__ import annotations

import logging
import re
from datetime import date, datetime

from scraper.http_client import HttpClient
from scraper.models import EventOccurrence, ScrapedEventRow
from scraper.parser import (
    is_bad_performer_name,
    parse_event_detail,
    parse_date_from_source_url,
    parse_month_occurrences,
    should_exclude_performer,
)

BASE_MONTH_URL = "https://www.dakotacooks.com/events/month/{year:04d}-{month:02d}/"


def iter_months(start_month: str, end_month: str) -> list[tuple[int, int]]:
    start = datetime.strptime(start_month, "%Y-%m")
    end = datetime.strptime(end_month, "%Y-%m")
    if start > end:
        raise ValueError("start-month must be <= end-month")
    months: list[tuple[int, int]] = []
    year = start.year
    month = start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return months


def scrape_range(start_month: str, end_month: str, logger: logging.Logger) -> list[ScrapedEventRow]:
    client = HttpClient()
    months = iter_months(start_month, end_month)
    logger.info("Scraping %d month(s) from %s to %s", len(months), start_month, end_month)

    rows: list[ScrapedEventRow] = []
    seen_rows: set[tuple[date, time | None, str, str]] = set()
    detail_cache: dict[str, tuple[str | None, str | None, str | None, date | None, str | None]] = {}
    warned_incomplete: set[str] = set()

    for year, month in months:
        month_url = BASE_MONTH_URL.format(year=year, month=month)
        logger.info("Fetching month page: %s", month_url)
        month_html = client.get_text(month_url)
        occurrences = parse_month_occurrences(month_html, month_url)
        logger.info("Discovered %d occurrence(s) in %04d-%02d", len(occurrences), year, month)
        for occurrence in occurrences:
            row = _build_row(client, occurrence, detail_cache, warned_incomplete, logger)
            if row:
                dedupe_key = (
                    row.event_date,
                    row.event_time or "",
                    _canonical_source_for_dedupe(row.source_url),
                )
                if dedupe_key in seen_rows:
                    continue
                seen_rows.add(dedupe_key)
                rows.append(row)
    logger.info("Prepared %d row(s) for database upsert", len(rows))
    return rows


def _build_row(
    client: HttpClient,
    occurrence: EventOccurrence,
    detail_cache: dict[str, tuple[str | None, str | None, str | None, date | None, str | None]],
    warned_incomplete: set[str],
    logger: logging.Logger,
) -> ScrapedEventRow | None:
    if occurrence.source_url not in detail_cache:
        logger.debug("Fetching detail page: %s", occurrence.source_url)
        detail_html = client.get_text(occurrence.source_url)
        detail = parse_event_detail(detail_html, occurrence.source_url)
        detail_cache[occurrence.source_url] = (
            detail.genre,
            detail.description_short,
            detail.performer_name,
            detail.event_date,
            detail.event_times_text,
        )
    genre, description_short, detail_name, detail_date, detail_times_text = detail_cache[occurrence.source_url]

    performer_name = occurrence.performer_name
    if is_bad_performer_name(performer_name) and detail_name:
        performer_name = detail_name
    elif not performer_name:
        performer_name = detail_name

    if should_exclude_performer(performer_name):
        logger.info("Skipping excluded performer row from %s", occurrence.source_url)
        return None

    event_date = occurrence.event_date or detail_date or parse_date_from_source_url(occurrence.source_url)
    event_time = detail_times_text
    if not event_time and occurrence.event_time:
        event_time = occurrence.event_time.strftime("%I:%M %p").lstrip("0")
    if not performer_name or not event_date:
        if occurrence.source_url not in warned_incomplete:
            missing: list[str] = []
            if not performer_name:
                missing.append("performer_name")
            if not event_date:
                missing.append("event_date")
            logger.warning(
                "Skipping incomplete event from %s (missing: %s)",
                occurrence.source_url,
                ", ".join(missing),
            )
            warned_incomplete.add(occurrence.source_url)
        return None
    return ScrapedEventRow(
        source_url=_canonical_source_for_dedupe(occurrence.source_url),
        performer_name=performer_name,
        event_date=event_date,
        event_time=event_time,
        genre=genre,
        description_short=description_short,
    )


def _canonical_source_for_dedupe(source_url: str) -> str:
    # Collapse duplicate list entries that differ only by trailing show index (/1/, /2/).
    return re.sub(r"/\d+/?$", "/", source_url.rstrip("/") + "/")
