import logging
import uuid
from enum import StrEnum, auto

import psycopg
from linebot.v3.messaging import FlexMessage, TextMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.updates as update_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


class FindEventSteps(StrEnum):
    INPUT_NAME = auto()


def _process_event_name_input(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage | TextMessage:
    logger.info("Processing find event name input")
    event_name = text

    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name input: {event_name}")
        logger.debug(f"Error msg={error_msg}")
        return TextMessage(text=error_msg)
    event_id = event_db.get_event_id(chat.user_id, event_name, conn)
    if event_id is None:
        logger.info(f"Event not found: {event_name}")
        return msg.info.event_name_not_found(event_name)

    event = event_db.get_event(event_id, conn)
    assert event is not None, "Event is not suppose to be missing"
    recent_update_times = update_db.list_event_recent_update_times(event_id, conn)
    logger.info("┌── Event Found ────────────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Cycle: {event.event_cycle}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info(f"│ Next Due: {event.next_due_at}")
    logger.info(f"│ Recent Updates: {len(recent_update_times)}")
    logger.info("└───────────────────────────────────────────")

    chat.current_step = None
    chat.status = ChatStatus.COMPLETED.value
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    chat_db.set_chat_status(chat.chat_id, chat.status, conn)
    logger.info(f"Setting current_step={chat.current_step}")
    logger.info(f"Finishing chat: {chat.chat_id}")
    return msg.events.find.format_event_summary(event, recent_update_times)


def create_find_event_chat(user_id: str, conn: psycopg.Connection) -> TextMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: find event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.FIND_EVENT.value,
        current_step=FindEventSteps.INPUT_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.find.prompt_for_event_name()


def handle_find_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage | TextMessage:
    if chat.current_step == FindEventSteps.INPUT_NAME:
        return _process_event_name_input(text, chat, conn)
    else:
        raise AssertionError(f"Unknown step in handle_find_event_chat: {chat.current_step}")
