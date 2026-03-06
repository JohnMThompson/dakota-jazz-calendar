from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class EventOccurrence:
    source_url: str
    performer_name: str
    event_date: date | None
    event_time: time | None


@dataclass(frozen=True)
class EventDetail:
    source_url: str
    genre: str | None
    description_short: str | None
    performer_name: str | None
    event_date: date | None
    event_time: time | None
    event_times_text: str | None


@dataclass(frozen=True)
class ScrapedEventRow:
    source_url: str
    performer_name: str
    event_date: date
    event_time: str | None
    genre: str | None
    description_short: str | None
