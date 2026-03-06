from __future__ import annotations

from datetime import date, time
from pathlib import Path

from scraper.parser import (
    is_bad_performer_name,
    parse_event_detail,
    parse_date_from_source_url,
    parse_month_occurrences,
    should_exclude_performer,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_month_occurrences_extracts_two_rows() -> None:
    html = _read("month_2026_03.html")
    rows = parse_month_occurrences(html, "https://www.dakotacooks.com/events/month/2026-03/")

    assert len(rows) == 2
    assert rows[0].performer_name == "Jane Doe Quartet"
    assert rows[0].event_date == date(2026, 3, 15)
    assert rows[0].event_time == time(19, 0)


def test_parse_event_detail_prefers_description_first_paragraph() -> None:
    html = _read("event_detail_jane.html")
    detail = parse_event_detail(html, "https://www.dakotacooks.com/event/jane-doe-quartet/")

    assert detail.genre == "Jazz"
    assert detail.description_short == "Jane Doe is a saxophonist known for modern post-bop arrangements."
    assert detail.performer_name == "Jane Doe Quartet"
    assert detail.event_date == date(2026, 3, 15)
    assert detail.event_time == time(19, 0)


def test_parse_event_detail_jsonld_fallback() -> None:
    html = _read("event_detail_jsonld.html")
    detail = parse_event_detail(html, "https://www.dakotacooks.com/event/fallback-artist/")

    assert detail.performer_name == "Fallback Artist"
    assert detail.event_date == date(2026, 4, 3)
    assert detail.event_time == time(21, 0)
    assert detail.description_short == "A one-line description from JSON-LD."


def test_parse_event_detail_elementor_fallback_text() -> None:
    html = _read("event_detail_elementor.html")
    detail = parse_event_detail(html, "https://www.dakotacooks.com/event/emmet-cohen-trio-mar1-2026/")

    assert detail.description_short is not None
    assert "Emmet Cohen" in detail.description_short
    assert detail.event_time is None


def test_parse_event_detail_showtimes_text() -> None:
    html = _read("event_detail_showtimes.html")
    detail = parse_event_detail(html, "https://www.dakotacooks.com/event/example-artist/")

    assert detail.event_times_text == "6:00 PM, 8:30 PM"


def test_bad_performer_name_heuristics_and_filtering() -> None:
    assert is_bad_performer_name("1")
    assert is_bad_performer_name("2026 03 11")
    assert is_bad_performer_name("Read More")
    assert not is_bad_performer_name("Emmet Cohen Trio")
    assert should_exclude_performer("Private Event")


def test_parse_date_from_source_url_patterns() -> None:
    assert parse_date_from_source_url("https://www.dakotacooks.com/event/los-lobos/2026-03-11/") == date(2026, 3, 11)
    assert parse_date_from_source_url("https://www.dakotacooks.com/event/sarah-morris-molly-dean-mar3-2026/") == date(2026, 3, 3)
