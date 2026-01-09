import logging
from datetime import datetime

import psycopg

from routine_bot.errors import EventNotFoundError
from routine_bot.logger import add_context, format_logger_name
from routine_bot.models import EventData

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
    logger.debug(f"Event inserted: {event.event_id}")


def get_event_by_id(event_id: str, conn: psycopg.Connection) -> EventData | None:
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


def get_event_by_name(user_id: str, event_name: str, conn: psycopg.Connection) -> EventData | None:
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
            WHERE user_id = %s AND event_name = %s
            """,
            (user_id, event_name),
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
        if cur.rowcount == 0:
            raise EventNotFoundError(f"Event not found: {event_id}")
    logger.debug(f"Event deleted: {event_id}")


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
            ORDER BY last_done_at DESC
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
            ORDER BY next_due_at ASC
            """,
            (user_id,),
        )
        result = cur.fetchall()
        return [EventData(*row) for row in result]


def set_event_name(event_id: str, event_name: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET event_name = %s
            WHERE event_id = %s
            """,
            (event_name, event_id),
        )
        if cur.rowcount == 0:
            raise EventNotFoundError(f"Event not found: {event_id}")
    ctx_logger = add_context(logger, event_id=event_id)
    ctx_logger.debug(f"Set event_name={event_name}")


def set_event_reminder_enabled(event_id: str, to: bool, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET reminder_enabled = %s
            WHERE event_id = %s
            """,
            (to, event_id),
        )
        if cur.rowcount == 0:
            raise EventNotFoundError(f"Event not found: {event_id}")
    ctx_logger = add_context(logger, event_id=event_id)
    ctx_logger.debug(f"Set reminder_enabled={to}")


def set_event_cycle(event_id: str, event_cycle: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET event_cycle = %s
            WHERE event_id = %s
            """,
            (event_cycle, event_id),
        )
        if cur.rowcount == 0:
            raise EventNotFoundError(f"Event not found: {event_id}")
    ctx_logger = add_context(logger, event_id=event_id)
    ctx_logger.debug(f"Set event_cycle={event_cycle}")


def set_event_last_done_at(event_id: str, last_done_at: datetime, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET last_done_at = %s
            WHERE event_id = %s
            """,
            (last_done_at, event_id),
        )
        if cur.rowcount == 0:
            raise EventNotFoundError(f"Event not found: {event_id}")
    ctx_logger = add_context(logger, event_id=event_id)
    ctx_logger.debug(f"Set last_done_at={last_done_at}")


def set_event_next_due_at(event_id: str, next_due_at: datetime, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET next_due_at = %s
            WHERE event_id = %s
            """,
            (next_due_at, event_id),
        )
        if cur.rowcount == 0:
            raise EventNotFoundError(f"Event not found: {event_id}")
    ctx_logger = add_context(logger, event_id=event_id)
    ctx_logger.debug(f"Set next_due_at={next_due_at}")


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
        if cur.rowcount == 0:
            raise EventNotFoundError(f"Event not found: {event_id}")
    ctx_logger = add_context(logger, event_id=event_id)
    ctx_logger.debug(f"Set is_active={to}")


def set_all_events_activeness_by_user(user_id: str, to: bool, conn: psycopg.Connection) -> None:
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
            ctx_logger = add_context(logger, event_id=row[0])
            ctx_logger.debug(f"Set is_active={to}")
    ctx_logger = add_context(logger, user_id=user_id)
    ctx_logger.debug(f"Set is_active={to} for all events")


def increment_event_share_count(event_id: str, by: int, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET share_count = share_count + %s
            WHERE event_id = %s
            RETURNING share_count
            """,
            (by, event_id),
        )
        result = cur.fetchone()
        if result is None:
            raise EventNotFoundError(f"Event not found: {event_id}")
    ctx_logger = add_context(logger, event_id=event_id)
    ctx_logger.debug(f"Set share_count={result[0]}")


def is_event_name_duplicated(user_id: str, event_name: str, conn: psycopg.Connection) -> bool:
    event_id = get_event_id(user_id, event_name, conn)
    if event_id is None:
        return False
    return True
