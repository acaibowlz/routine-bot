import logging
from datetime import datetime

import psycopg

from routine_bot.logger import add_context, format_logger_name
from routine_bot.models import RecordData

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
    ctx_logger = add_context(logger, record_id=record.record_id)
    ctx_logger.debug("Record inserted")


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


def delete_records_by_event(event_id: str, conn: psycopg.Connection) -> None:
    ctx_logger = add_context(logger, event_id=event_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM records
            WHERE event_id = %s
            RETURNING record_id
            """,
            (event_id,),
        )
        deleted_records = [row[0] for row in cur.fetchall()]
        for record_id in deleted_records:
            ctx_logger.debug(f"Record deleted: {record_id}")
