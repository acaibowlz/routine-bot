import logging
from datetime import datetime

import psycopg

from routine_bot.models import UpdateData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def add_update(update: UpdateData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO updates (update_id, event_id, event_name, user_id, done_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                update.update_id,
                update.event_id,
                update.event_name,
                update.user_id,
                update.done_at,
            ),
        )
    conn.commit()
    logger.debug(f"Update inserted: {update.update_id}")


def list_event_recent_update_times(event_id: str, conn: psycopg.Connection, limit: int = 10) -> list[datetime]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT done_at
            FROM updates
            WHERE event_id = %s
            ORDER BY done_at DESC
            LIMIT %s
            """,
            (event_id, limit),
        )
        result = cur.fetchall()
        return [row[0] for row in result]


def delete_updates_by_event_id(event_id: str, conn: psycopg.Connection) -> None:
    logger.debug(f"Deleting updates by event_id: {event_id}")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT update_id
            FROM updates
            WHERE event_id = %s
            """,
            (event_id,),
        )
        update_ids = [row[0] for row in cur.fetchall()]

        cur.execute(
            """
            DELETE FROM updates
            WHERE event_id = %s
            """,
            (event_id,),
        )
    conn.commit()
    for update_id in update_ids:
        logger.debug(f"Update deleted: {update_id}")
