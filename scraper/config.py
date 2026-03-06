from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    name: str
    user: str
    password: str


def load_db_config() -> DBConfig:
    load_dotenv()
    return DBConfig(
        host=_required("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        name=_required("DB_NAME"),
        user=_required("DB_USER"),
        password=_required("DB_PASSWORD"),
    )


def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value
