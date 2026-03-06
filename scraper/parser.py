from __future__ import annotations

import json
import re
from datetime import date, datetime, time
from html import unescape
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from scraper.models import EventDetail, EventOccurrence

_TIME_PATTERN = re.compile(r"(\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?)", re.IGNORECASE)
_CLOCK_TIME_TEXT_PATTERN = re.compile(r"^\s*(\d{1,2}:\d{2})\s*([ap])\.?\s*m\.?\s*$", re.IGNORECASE)
_URL_DATE_SEGMENT_PATTERN = re.compile(r"/((?:19|20)\d{2}-\d{2}-\d{2})(?:/|$)")
_URL_SLUG_DATE_PATTERN = re.compile(
    r"-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\d{1,2})-(\d{4})(?:/|$)",
    re.IGNORECASE,
)


def parse_month_occurrences(html: str, base_url: str) -> list[EventOccurrence]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[EventOccurrence] = []
    seen: set[tuple[str, date | None, time | None, str]] = set()

    containers = soup.select(
        "article, div[class*='tribe-events-calendar-month__calendar-event'], div[class*='tribe-events-calendar-list__event-row']"
    )
    if not containers:
        containers = [soup]  # Fallback for unexpected markup.

    for container in containers:
        link = _find_event_link(container, base_url)
        if not link:
            continue
        performer_name = _extract_name(container, link)
        date_value, time_value = _extract_date_time(container)
        key = (link, date_value, time_value, performer_name.lower())
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            EventOccurrence(
                source_url=link,
                performer_name=performer_name,
                event_date=date_value,
                event_time=time_value,
            )
        )
    return rows


def parse_event_detail(html: str, source_url: str) -> EventDetail:
    soup = BeautifulSoup(html, "html.parser")
    performer_name = _extract_detail_name(soup)
    event_date, event_time = _extract_detail_datetime(soup)
    if not event_date:
        event_date = parse_date_from_source_url(source_url)
    event_times_text = _extract_event_times_text(soup)
    genre = _extract_genre(soup)
    description_short = _extract_first_paragraph(soup)

    return EventDetail(
        source_url=source_url,
        genre=genre,
        description_short=description_short,
        performer_name=performer_name,
        event_date=event_date,
        event_time=event_time,
        event_times_text=event_times_text,
    )


def _find_event_link(container: Tag, base_url: str) -> str | None:
    for anchor in container.find_all("a", href=True):
        href = anchor["href"].strip()
        if "/event/" in href:
            return urljoin(base_url, href)
    return None


def _extract_name(container: Tag, fallback_link: str) -> str:
    selectors = [
        "h3 a",
        "h2 a",
        "a[class*='event-title']",
        "a[class*='event-link']",
    ]
    for selector in selectors:
        node = container.select_one(selector)
        if node and node.get_text(strip=True):
            candidate = _clean_text(node.get_text(" ", strip=True))
            if not is_bad_performer_name(candidate):
                return candidate

    anchor = container.find("a", href=True)
    if anchor and anchor.get_text(strip=True):
        candidate = _clean_text(anchor.get_text(" ", strip=True))
        if not is_bad_performer_name(candidate):
            return candidate
    path = urlparse(fallback_link).path.strip("/").split("/")
    return _clean_text(path[-1].replace("-", " ")) if path else "Unknown Performer"


def _extract_date_time(container: Tag) -> tuple[date | None, time | None]:
    for node in container.find_all("time"):
        raw_datetime = node.get("datetime")
        parsed = _parse_iso(raw_datetime)
        if parsed:
            return parsed.date(), normalize_event_time(raw_datetime, parsed)

    text = container.get_text(" ", strip=True)
    date_value = _parse_date_from_text(text)
    time_value = _parse_time_from_text(text)
    return date_value, time_value


def _extract_detail_name(soup: BeautifulSoup) -> str | None:
    title = soup.select_one("h1")
    if title and title.get_text(strip=True):
        return _clean_text(title.get_text(" ", strip=True))
    event_data = _extract_event_json_ld(soup)
    if event_data and event_data.get("name"):
        return _clean_text(str(event_data["name"]))
    return None


def _extract_detail_datetime(soup: BeautifulSoup) -> tuple[date | None, time | None]:
    for node in soup.find_all("time"):
        raw_datetime = node.get("datetime")
        parsed = _parse_iso(raw_datetime)
        if parsed:
            return parsed.date(), normalize_event_time(raw_datetime, parsed)

    event_data = _extract_event_json_ld(soup)
    if event_data and event_data.get("startDate"):
        raw_datetime = str(event_data["startDate"])
        parsed = _parse_iso(raw_datetime)
        if parsed:
            return parsed.date(), normalize_event_time(raw_datetime, parsed)
    return None, None


def _extract_genre(soup: BeautifulSoup) -> str | None:
    for selector in [
        "a[rel='tag']",
        "dd.tribe-events-event-categories a",
        "a[href*='/events/category/']",
    ]:
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return _clean_text(node.get_text(" ", strip=True))
    return None


def _extract_first_paragraph(soup: BeautifulSoup) -> str | None:
    for selector in [
        ".tribe-events-single-event-description p",
        ".event-description p",
        "article p",
        "main p",
    ]:
        for node in soup.select(selector):
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                return text

    # Dakota pages often render copy with Elementor wrappers and no <p> tags.
    for selector in [
        ".event-content",
        ".elementor-widget-theme-post-content",
        ".tribe-events-single-event-description",
        ".tribe-events-content",
    ]:
        node = soup.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                return text

    event_data = _extract_event_json_ld(soup)
    if event_data and event_data.get("description"):
        text = _clean_text(str(event_data["description"]))
        # JSON-LD descriptions can be full text. Keep the first sentence-like chunk.
        return text.split("\n", 1)[0].strip() if text else None
    return None


def _extract_event_json_ld(soup: BeautifulSoup) -> dict | None:
    for node in soup.select("script[type='application/ld+json']"):
        raw = node.string or node.get_text()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "Event":
                return item
    return None


def parse_date_from_source_url(source_url: str) -> date | None:
    segment_match = _URL_DATE_SEGMENT_PATTERN.search(source_url)
    if segment_match:
        try:
            return datetime.strptime(segment_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

    slug_match = _URL_SLUG_DATE_PATTERN.search(source_url)
    if slug_match:
        month_abbrev, day, year = slug_match.groups()
        try:
            parsed = datetime.strptime(
                f"{month_abbrev.title()} {int(day):02d} {year}",
                "%b %d %Y",
            )
            return parsed.date()
        except ValueError:
            return None
    return None


def _extract_event_times_text(soup: BeautifulSoup) -> str | None:
    labels: list[str] = []
    selectors = [
        ".event-schedule a[data-occurrence-id]",
        ".event-time a",
        "a[data-occurrence-id]",
    ]
    for selector in selectors:
        for node in soup.select(selector):
            text = _normalize_clock_time_text(node.get_text(" ", strip=True))
            if text:
                labels.append(text)
    if not labels:
        return None

    unique = sorted(set(labels), key=_time_sort_key)
    return ", ".join(unique)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        clean = value.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except ValueError:
        return None


def is_bad_performer_name(value: str | None) -> bool:
    if not value:
        return True
    text = _clean_text(value)
    if not text:
        return True
    lower = text.lower()
    if lower == "private event":
        return True
    if lower in {"read more", "buy tickets", "tickets", "ticket"}:
        return True
    if text.isdigit():
        return True
    if re.fullmatch(r"\d{4}\s+\d{1,2}\s+\d{1,2}", text):
        return True
    return False


def should_exclude_performer(value: str | None) -> bool:
    if not value:
        return False
    return "private event" in _clean_text(value).lower()


def normalize_event_time(value: str | None, parsed: datetime | None) -> time | None:
    if not parsed:
        return None
    if not value:
        return parsed.time().replace(second=0, microsecond=0)
    raw = value.strip()
    if "T" not in raw and " " not in raw:
        return None
    candidate = parsed.time().replace(second=0, microsecond=0)
    return None if candidate == time(0, 0) else candidate


def _parse_date_from_text(text: str) -> date | None:
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    date_match = re.search(r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", text)
    if not date_match:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_match.group(1), fmt).date()
        except ValueError:
            continue
    return None


def _parse_time_from_text(text: str) -> time | None:
    match = _TIME_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(1).lower().replace(".", "").replace(" ", "")
    for fmt in ("%I:%M%p",):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _normalize_clock_time_text(value: str) -> str | None:
    if not value:
        return None
    match = _CLOCK_TIME_TEXT_PATTERN.match(value)
    if not match:
        return None
    hhmm = match.group(1)
    ampm = match.group(2).upper()
    return f"{hhmm} {ampm}M"


def _time_sort_key(label: str) -> tuple[int, int]:
    parsed = _parse_time_from_text(label)
    if not parsed:
        return (99, 99)
    return (parsed.hour, parsed.minute)
