import logging

import psycopg
from psycopg.types.json import Json

from routine_bot.enums.chat import ChatStatus
from routine_bot.enums.steps import BaseSteps
from routine_bot.errors import ChatNotFoundError
from routine_bot.logger import add_context, format_logger_name
from routine_bot.models import ChatData

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


def get_ongoing_chat(user_id: str, conn: psycopg.Connection) -> ChatData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id, user_id, chat_type, current_step, payload, status
            FROM chats
            WHERE user_id = %s AND status = %s
            """,
            (user_id, ChatStatus.ONGOING.value),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return ChatData(*result)


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
        if cur.rowcount == 0:
            raise ChatNotFoundError(f"Chat not found: {chat_id}")
    ctx_logger = add_context(logger, chat_id=chat_id)
    ctx_logger.debug(f"Set payload={payload}")


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
        if cur.rowcount == 0:
            raise ChatNotFoundError(f"Chat not found: {chat_id}")
    ctx_logger = add_context(logger, chat_id=chat_id)
    ctx_logger.debug(f"Set current_step={current_step}")


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
        if cur.rowcount == 0:
            raise ChatNotFoundError(f"Chat not found: {chat_id}")
    ctx_logger = add_context(logger, chat_id=chat_id)
    ctx_logger.debug(f"Set status={status}")


def patch_chat_payload(
    chat: ChatData, new_data: dict[str, str], conn: psycopg.Connection, logger: logging.Logger
) -> dict[str, str]:
    ctx_logger = add_context(logger, chat_id=chat.chat_id)
    for key, val in new_data.items():
        if chat.payload.get(key) is None:
            ctx_logger.debug(f"Adding to payload: {key}={val}")
        else:
            ctx_logger.debug(f"Overwriting payload: {key}={val} (was {chat.payload[key]})")
        chat.payload[key] = val
    set_chat_payload(chat.chat_id, chat.payload, conn)
    return chat.payload


def finalize_chat(chat: ChatData, conn: psycopg.Connection, logger: logging.Logger) -> None:
    set_chat_current_step(chat.chat_id, BaseSteps.COMPLETED.value, conn)
    set_chat_status(chat.chat_id, ChatStatus.COMPLETED.value, conn)
    ctx_logger = add_context(logger, chat_id=chat.chat_id)
    ctx_logger.info("Chat finalized")
