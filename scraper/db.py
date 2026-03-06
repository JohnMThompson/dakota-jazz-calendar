from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pymysql

from scraper.config import DBConfig
from scraper.models import ScrapedEventRow


def connect(config: DBConfig) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.name,
        autocommit=True,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
    )


def ensure_schema(connection: pymysql.connections.Connection) -> None:
    schema_path = Path(__file__).resolve().parent.parent / "schema.sql"
    ddl = schema_path.read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        cursor.execute(ddl)
        # Keep legacy tables compatible with the current uniqueness behavior.
        cursor.execute(
            "ALTER TABLE dakota_events MODIFY COLUMN event_time VARCHAR(64) NOT NULL DEFAULT ''"
        )


def upsert_events(connection: pymysql.connections.Connection, events: list[ScrapedEventRow]) -> int:
    if not events:
        return 0
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    rows = [
        (
            item.event_date.strftime("%Y-%m-%d"),
            item.event_time or "",
            item.performer_name,
            item.genre,
            item.description_short,
            item.source_url,
            now,
            now,
        )
        for item in events
    ]
    query = """
        INSERT INTO dakota_events (
            event_date,
            event_time,
            performer_name,
            genre,
            description_short,
            source_url,
            scraped_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            genre = VALUES(genre),
            description_short = VALUES(description_short),
            source_url = VALUES(source_url),
            updated_at = VALUES(updated_at)
    """
    with connection.cursor() as cursor:
        cursor.executemany(query, rows)
    return len(rows)
