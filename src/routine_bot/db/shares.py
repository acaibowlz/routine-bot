import logging

import psycopg

from routine_bot.models import EventData, ShareData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def add_share(share: ShareData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO shares (share_id, event_id, event_name, owner_id, recipient_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                share.share_id,
                share.event_id,
                share.event_name,
                share.owner_id,
                share.recipient_id,
            ),
        )
    logger.debug(f"Inserting share: {share.share_id}")


def list_shared_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                e.event_id,
                e.user_id,
                e.event_name,
                e.reminder_enabled,
                e.event_cycle,
                e.last_done_at,
                e.next_due_at,
                e.share_count,
                e.is_active
            FROM events e
            WHERE EXISTS (
                SELECT 1
                FROM shares s
                WHERE s.recipient_id = %s
                AND s.event_id = e.event_id
            )
            """,
            (user_id,),
        )
        result = cur.fetchall()
        return [EventData(*row) for row in result]


def list_overdue_shared_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                e.event_id,
                e.user_id,
                e.event_name,
                e.reminder_enabled,
                e.event_cycle,
                e.last_done_at,
                e.next_due_at,
                e.share_count,
                e.is_active
            FROM events e
            WHERE e.reminder_enabled = TRUE
            AND e.next_due_at <= NOW()
            AND EXISTS (
                SELECT 1
                FROM shares s
                WHERE s.recipient_id = %s
                AND s.event_id = e.event_id
            )
            """,
            (user_id,),
        )
        result = cur.fetchall()
        return [EventData(*row) for row in result]


def delete_shares_by_event_id(event_id: str, conn: psycopg.Connection):
    logger.debug(f"Deleting shares by event_id: {event_id}")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT share_id
            FROM shares
            WHERE event_id = %s
            """,
            (event_id,),
        )
        share_ids = [row[0] for row in cur.fetchall()]
        for share_id in share_ids:
            logger.debug(f"Deleting share: {share_id}")

        cur.execute(
            """
            DELETE FROM shares
            WHERE event_id = %s
            """,
            (event_id,),
        )
        return share_ids
