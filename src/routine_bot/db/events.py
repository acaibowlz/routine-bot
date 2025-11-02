import logging

import psycopg

from routine_bot.models import EventData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def add_event(event: EventData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (
                event_id,
                user_id,
                event_name,
                reminder_enabled,
                event_cycle,
                last_done_at,
                next_due_at,
                share_count,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event.event_id,
                event.user_id,
                event.event_name,
                event.reminder_enabled,
                event.event_cycle,
                event.last_done_at,
                event.next_due_at,
                0,
                True,
            ),
        )
    logger.debug(f"Inserting event: {event.event_id}")


def get_event(event_id: str, conn: psycopg.Connection) -> EventData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                event_id,
                user_id,
                event_name,
                reminder_enabled,
                event_cycle,
                last_done_at,
                next_due_at,
                share_count,
                is_active
            FROM events
            WHERE event_id = %s
            """,
            (event_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return EventData(*result)


def delete_event(event_id: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM events
            WHERE event_id = %s
            """,
            (event_id,),
        )
    logger.debug(f"Deleting event: {event_id}")


def get_event_id(user_id: str, event_name: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT event_id
            FROM events
            WHERE user_id = %s AND event_name = %s
            """,
            (user_id, event_name),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def list_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                event_id,
                user_id,
                event_name,
                reminder_enabled,
                event_cycle,
                last_done_at,
                next_due_at,
                share_count,
                is_active
            FROM events
            WHERE user_id = %s
            """,
            (user_id,),
        )
        result = cur.fetchall()
        return [EventData(*row) for row in result]


def list_overdue_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                event_id,
                user_id,
                event_name,
                reminder_enabled,
                event_cycle,
                last_done_at,
                next_due_at,
                share_count,
                is_active
            FROM events
            WHERE user_id = %s
            AND reminder_enabled = TRUE
            AND next_due_at <= NOW()
            """,
            (user_id,),
        )
        result = cur.fetchall()
        return [EventData(*row) for row in result]


def set_event_activeness(event_id: str, to: bool, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET is_active = %s
            WHERE event_id = %s
            """,
            (to, event_id),
        )
    logger.debug(f"Updating is_active for event: {event_id}")


def set_all_events_activeness_by_user(user_id: str, to: bool, conn: psycopg.Connection) -> None:
    logger.debug(f"Updating all events activeness for user: {user_id}")
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET is_active = %s
            WHERE user_id = %s
            RETURNING event_id
            """,
            (to, user_id),
        )
        result = cur.fetchall()
        for row in result:
            logger.debug(f"Updating is_active for event: {row[0]}")
