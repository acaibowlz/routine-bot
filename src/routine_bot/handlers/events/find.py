import logging
import uuid

import psycopg
from linebot.v3.messaging import FlexMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.records as record_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import FindEventSteps
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name_entry(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    logger.info("Processing find event name entry")
    event_name = text

    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name entry: {event_name}, error msg={error_msg}")
        return msg.error.error([error_msg])
    event_id = event_db.get_event_id(chat.user_id, event_name, conn)
    if event_id is None:
        logger.info(f"Event not found: {event_name}")
        return msg.error.event_name_not_found(event_name)

    event = event_db.get_event(event_id, conn)
    assert event is not None, "Event is not suppose to be missing"
    recent_records = record_db.list_event_recent_records(event_id, conn)
    logger.info("┌── Event Found ────────────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Cycle: {event.event_cycle}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info(f"│ Next Due: {event.next_due_at}")
    logger.info(f"│ Recent Records: {len(recent_records)}")
    logger.info("└───────────────────────────────────────────")

    chat.current_step = None
    chat.status = ChatStatus.COMPLETED.value
    logger.info(f"Setting current_step={chat.current_step}")
    logger.info(f"Finishing chat: {chat.chat_id}")
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    chat_db.set_chat_status(chat.chat_id, chat.status, conn)
    return msg.events.find.format_event_summary(event, recent_records)


def create_find_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: find event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.FIND_EVENT.value,
        current_step=FindEventSteps.ENTER_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.find.enter_event_name()


def handle_find_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    if chat.current_step == FindEventSteps.ENTER_NAME:
        return _process_event_name_entry(text, chat, conn)
    else:
        raise AssertionError(f"Unknown step in handle_find_event_chat: {chat.current_step}")
