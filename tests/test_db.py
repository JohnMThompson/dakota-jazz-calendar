from __future__ import annotations

from scraper.db import _get_unique_index_columns


class FakeCursor:
    def __init__(self, rows: list[tuple]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, tuple[str, ...]]] = []

    def execute(self, query: str, params: tuple[str, ...]) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[tuple]:
        return self.rows


def test_get_unique_index_columns_returns_columns_in_sequence_order() -> None:
    cursor = FakeCursor(
        [
            ("dakota_events", 0, "uq_event_occurrence", 2, "source_url"),
            ("dakota_events", 0, "uq_event_occurrence", 1, "event_time"),
            ("dakota_events", 0, "uq_event_occurrence", 0, "event_date"),
        ]
    )

    columns = _get_unique_index_columns(cursor, "dakota_events", "uq_event_occurrence")

    assert columns == ("event_date", "event_time", "source_url")
