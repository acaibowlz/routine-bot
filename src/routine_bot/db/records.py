import logging
from datetime import datetime

import psycopg

from routine_bot.models import RecordData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def add_record(record: RecordData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO records (record_id, event_id, event_name, user_id, done_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                record.record_id,
                record.event_id,
                record.event_name,
                record.user_id,
                record.done_at,
            ),
        )
    logger.debug(f"Inserting record: {record.record_id}")


def list_event_recent_records(event_id: str, conn: psycopg.Connection, limit: int = 10) -> list[datetime]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT done_at
            FROM records
            WHERE event_id = %s
            ORDER BY done_at DESC
            LIMIT %s
            """,
            (event_id, limit),
        )
        result = cur.fetchall()
        return [row[0] for row in result]


def delete_records_by_event_id(event_id: str, conn: psycopg.Connection) -> list[str]:
    logger.debug(f"Deleting records by event_id: {event_id}")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT record_id
            FROM records
            WHERE event_id = %s
            """,
            (event_id,),
        )
        record_ids = [row[0] for row in cur.fetchall()]
        for record_id in record_ids:
            logger.debug(f"Deleting record: {record_id}")

        cur.execute(
            """
            DELETE FROM records
            WHERE event_id = %s
            """,
            (event_id,),
        )
        return record_ids
