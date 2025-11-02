import logging

import psycopg
from psycopg.types.json import Json

from routine_bot.enums.chat import ChatStatus
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def add_chat(chat: ChatData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chats (chat_id, user_id, chat_type, current_step, payload, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                chat.chat_id,
                chat.user_id,
                chat.chat_type,
                chat.current_step,
                Json(chat.payload),
                chat.status,
            ),
        )
    conn.commit()
    logger.debug(f"Chat inserted: {chat.chat_id}")


def get_chat(chat_id: str, conn: psycopg.Connection) -> ChatData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id, user_id, chat_type, current_step, payload, status
            FROM chats
            WHERE chat_id = %s
            """,
            (chat_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return ChatData(*result)


def get_ongoing_chat_id(user_id: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id
            FROM chats
            WHERE user_id = %s AND status = %s
            """,
            (user_id, ChatStatus.ONGOING.value),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def set_chat_current_step(chat_id: str, current_step: str | None, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET current_step = %s
            WHERE chat_id = %s
            """,
            (current_step, chat_id),
        )
    conn.commit()
    logger.debug(f"Chat current_step updated: {chat_id}")


def set_chat_payload(chat_id: str, payload: dict, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET payload = %s
            WHERE chat_id = %s
            """,
            (Json(payload), chat_id),
        )
    conn.commit()
    logger.debug(f"Chat payload updated: {chat_id}")


def set_chat_status(chat_id: str, status: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET status = %s
            WHERE chat_id = %s
            """,
            (status, chat_id),
        )
    conn.commit()
    logger.debug(f"Chat status updated: {chat_id}")
