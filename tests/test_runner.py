from __future__ import annotations

import pytest
import requests

import scraper.runner as runner
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


def test_scrape_range_stops_cleanly_at_first_missing_month_page(monkeypatch, caplog) -> None:
    requested_urls: list[str] = []
    caplog.set_level("INFO")

    class FakeClient:
        def get_text(self, url: str) -> str:
            requested_urls.append(url)
            if url.endswith("2026-05/"):
                response = requests.Response()
                response.status_code = 404
                response.url = url
                raise requests.HTTPError(response=response)
            return "<html></html>"

    monkeypatch.setattr(runner, "HttpClient", FakeClient)
    monkeypatch.setattr(runner, "parse_month_occurrences", lambda *_: [])

    assert runner.scrape_range("2026-03", "2026-06", runner.logging.getLogger("test")) == []
    assert requested_urls == [
        "https://www.dakotacooks.com/events/month/2026-03/",
        "https://www.dakotacooks.com/events/month/2026-04/",
        "https://www.dakotacooks.com/events/month/2026-05/",
    ]
    assert "No published calendar page for 2026-05; ending month scan" in caplog.text
