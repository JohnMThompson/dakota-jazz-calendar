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
        cursor.execute(
            "ALTER TABLE dakota_events MODIFY COLUMN event_time VARCHAR(64) NOT NULL DEFAULT ''"
        )
        _dedupe_existing_rows(cursor)
        _ensure_unique_index(cursor)


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


def _dedupe_existing_rows(cursor: pymysql.cursors.Cursor) -> None:
    cursor.execute(
        """
        DELETE victim
        FROM dakota_events AS victim
        INNER JOIN dakota_events AS survivor
            ON survivor.event_date = victim.event_date
            AND survivor.event_time = victim.event_time
            AND survivor.source_url = victim.source_url
            AND (
                survivor.updated_at > victim.updated_at
                OR (
                    survivor.updated_at = victim.updated_at
                    AND survivor.id > victim.id
                )
            )
        """
    )


def _ensure_unique_index(cursor: pymysql.cursors.Cursor) -> None:
    current_columns = _get_unique_index_columns(cursor, "dakota_events", "uq_event_occurrence")
    desired_columns = ("event_date", "event_time", "source_url")

    if current_columns == desired_columns:
        return

    if current_columns:
        cursor.execute("ALTER TABLE dakota_events DROP INDEX uq_event_occurrence")

    cursor.execute(
        """
        ALTER TABLE dakota_events
        ADD UNIQUE KEY uq_event_occurrence (event_date, event_time, source_url)
        """
    )


def _get_unique_index_columns(
    cursor: pymysql.cursors.Cursor, table_name: str, index_name: str
) -> tuple[str, ...]:
    cursor.execute(f"SHOW INDEX FROM {table_name} WHERE Key_name = %s", (index_name,))
    rows = cursor.fetchall()
    if not rows:
        return ()
    sorted_rows = sorted(rows, key=lambda row: row[3])
    return tuple(row[4] for row in sorted_rows)
