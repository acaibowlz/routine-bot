import logging
from datetime import time

import psycopg

from routine_bot.models import UserData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def add_user(user_id: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (user_id)
            VALUES (%s)
            """,
            (user_id,),
        )
    conn.commit()
    logger.debug(f"User inserted: {user_id}")


def get_user(user_id: str, conn: psycopg.Connection) -> UserData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                user_id,
                event_count,
                notification_slot,
                is_premium,
                premium_until,
                is_active
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return UserData(*result)


def user_exists(user_id: str, conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM users
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone() is not None


def list_active_users_by_notification_slot(time_slot: time, conn: psycopg.Connection) -> list[UserData]:
    if time_slot.minute or time_slot.second or time_slot.microsecond:
        raise ValueError(f"Not a valid time slot: {time_slot}")
    logger.info(f"Current notification slot: {time_slot.strftime('%H:%M')}")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                user_id,
                event_count,
                notification_slot,
                is_premium,
                premium_until,
                is_active
            FROM users
            WHERE notification_slot = %s
            AND is_active = TRUE
            """,
            (time_slot,),
        )
        result = cur.fetchall()
        if len(result):
            logger.info(f"{len(result)} active users found within current time slot")
        else:
            logger.info("No active user found within current time slot")
        return [UserData(*row) for row in result]


def increment_user_event_count(user_id: str, by: int, conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET event_count = event_count + %s
            WHERE user_id = %s
            """,
            (by, user_id),
        )
    conn.commit()
    logger.debug(f"User event_count incremented by {by}: {user_id}")


def set_user_activeness(user_id: str, to: bool, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET is_active = %s
            WHERE user_id = %s
            """,
            (to, user_id),
        )
    conn.commit()
    logger.debug(f"User is_active updated: {user_id}")


def set_user_notification_slot(user_id: str, time_slot: time, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET notification_slot = %s
            WHERE user_id = %s
            """,
            (time_slot, user_id),
        )
    conn.commit()
    logger.debug(f"User notification_slot updated: {user_id}")
