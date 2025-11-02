import logging
import uuid

import psycopg
from linebot.v3.messaging import FlexMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def create_view_all_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: view all")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.VIEW_ALL.value,
        current_step=None,
        payload={},
        status=ChatStatus.COMPLETED.value,
    )
    chat_db.add_chat(chat, conn)

    events = event_db.list_events_by_user(user_id, conn)
    logger.info(f"Found {len(events)} events")
    logger.info(f"Finishing chat: {chat.chat_id}")
    return msg.events.view_all.format_all_events_summary(events)
