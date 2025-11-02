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
    logger.debug(f"Inserting user: {user_id}")


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
        return [UserData(*row) for row in result]


def increment_user_event_count(user_id: str, by: int, conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET event_count = event_count + %s
            WHERE user_id = %s
            RETURNING event_count
            """,
            (by, user_id),
        )
        result = cur.fetchone()
        assert result is not None, "User is not suppose to be missing"
        return result[0]


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
    logger.debug(f"Updating is_active for user: {user_id}")


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
    logger.debug(f"Updating notification_slot for user: {user_id}")
