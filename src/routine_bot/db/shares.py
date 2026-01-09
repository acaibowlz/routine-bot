import logging

import psycopg

from routine_bot.errors import ShareNotFoundError
from routine_bot.logger import add_context, format_logger_name
from routine_bot.models import EventData, ShareData

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
    logger.debug(f"Share inserted: {share.share_id}")


def get_share_by_event(event_id: str, recipient_id: str, conn: psycopg.Connection) -> ShareData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT share_id, event_id, event_name, owner_id, recipient_id
            FROM shares
            WHERE event_id = %s AND recipient_id = %s
            """,
            (event_id, recipient_id),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return ShareData(*result)


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


def delete_share(event_id: str, recipient_id: str, conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM shares
            WHERE event_id = %s AND recipient_id = %s
            RETURNING share_id
            """,
            (event_id, recipient_id),
        )
        result = cur.fetchone()
        if result is None:
            raise ShareNotFoundError(f"Share not found: event_id={event_id}, recipient_id={recipient_id}")
    logger.debug(f"Share deleted: {result[0]}")


def delete_shares_by_event(event_id: str, conn: psycopg.Connection):
    ctx_logger = add_context(logger, event_id=event_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM shares
            WHERE event_id = %s
            RETURNING share_id
            """,
            (event_id,),
        )
        deleted_shares = cur.fetchall()
        for share_id in deleted_shares:
            ctx_logger.debug(f"Share deleted: {share_id}")


def list_recipients_by_event(event_id: str, conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT recipient_id
            FROM shares
            WHERE event_id = %s
            """,
            (event_id,),
        )
        result = cur.fetchall()
        return [row[0] for row in result]


def is_share_duplicated(event_id: str, recipient_id: str, conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM shares
            WHERE event_id = %s AND recipient_id = %s
            LIMIT 1
            """,
            (event_id, recipient_id),
        )
        return cur.fetchone() is not None
