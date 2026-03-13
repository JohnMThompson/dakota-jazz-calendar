from __future__ import annotations

import pytest

from scraper.runner import _canonical_source_for_dedupe, iter_months


def test_iter_months_inclusive_range() -> None:
    assert iter_months("2026-03", "2026-05") == [(2026, 3), (2026, 4), (2026, 5)]


def test_iter_months_crosses_year_boundary() -> None:
    assert iter_months("2026-11", "2027-02") == [
        (2026, 11),
        (2026, 12),
        (2027, 1),
        (2027, 2),
    ]


def test_iter_months_rejects_reverse_range() -> None:
    with pytest.raises(ValueError):
        iter_months("2026-04", "2026-03")


def test_canonical_source_strips_trailing_show_index() -> None:
    assert _canonical_source_for_dedupe(
        "https://www.dakotacooks.com/event/example/2026-03-01/2/"
    ) == "https://www.dakotacooks.com/event/example/2026-03-01/"


def test_canonical_source_preserves_base_occurrence_url() -> None:
    assert _canonical_source_for_dedupe(
        "https://www.dakotacooks.com/event/example/2026-03-01/"
    ) == "https://www.dakotacooks.com/event/example/2026-03-01/"
