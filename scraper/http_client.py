from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class HttpClient:
    def __init__(self, timeout_seconds: int = 20, pause_seconds: float = 0.2) -> None:
        self._timeout_seconds = timeout_seconds
        self._pause_seconds = pause_seconds
        self._session = requests.Session()
        retries = Retry(
            total=4,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self._session.headers.update(
            {
                "User-Agent": "dakota-jazz-calendar-scraper/0.1 (+https://github.com/)",
            }
        )
        self._session.mount("http://", HTTPAdapter(max_retries=retries))
        self._session.mount("https://", HTTPAdapter(max_retries=retries))

    def get_text(self, url: str) -> str:
        response = self._session.get(url, timeout=self._timeout_seconds)
        response.raise_for_status()
        time.sleep(self._pause_seconds)
        return response.text

