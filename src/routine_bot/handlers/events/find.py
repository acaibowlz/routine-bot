import logging
import uuid
from datetime import datetime

import psycopg
from linebot.v3.messaging import FlexMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.records as record_db
import routine_bot.messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import FindEventSteps
from routine_bot.errors import InvalidStepError
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, get_time_diff, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    logger.info("Processing event name")
    event_name = text
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name. Input: {event_name}, Error msg: {''.join(error_msg)}")
        return msg.error.error(error_msg)
    user_id = chat.user_id
    event = event_db.get_event_by_name(user_id, event_name, conn)
    if event is None:
        logger.info(f"Event not found. User ID: {user_id}, Event Name: {event_name}")
        return msg.error.event_name_not_found(event_name)

    recent_records = record_db.list_event_recent_records(event.event_id, conn)
    logger.info("┌── Event Found ────────────────────────────")
    logger.info(f"│ Event Name: {event_name}")
    logger.info(f"│ Event ID: {event.event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Cycle: {event.event_cycle}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info(f"│ Next Due: {event.next_due_at}")
    logger.info(f"│ Recent Records: {len(recent_records)}")
    logger.info("└───────────────────────────────────────────")
    chat_db.finalize_chat(chat, conn, logger)

    payload = {}
    payload["event_name"] = event.event_name
    now = datetime.today().astimezone(TZ_TAIPEI)
    last_done_at = event.last_done_at.astimezone(tz=TZ_TAIPEI)
    payload["time_diff"] = get_time_diff(now, last_done_at)
    if event.reminder_enabled and event.next_due_at is not None:
        payload["reminder"] = "True"
        next_due_at = event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime("%Y-%m-%d")
        payload["next_due_at"] = next_due_at
        payload["event_cycle"] = event.event_cycle
    else:
        payload["reminder"] = "False"
    recent_records = [t.astimezone(tz=TZ_TAIPEI).strftime("%Y-%m-%d") for t in recent_records]
    payload["recent_records"] = recent_records
    chat.payload = chat_db.update_chat_payload(chat=chat, new_data=payload, conn=conn, logger=logger)

    return msg.events.find.format_event_summary(chat.payload)


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
    handlers = {FindEventSteps.ENTER_NAME.value: _process_event_name}
    handler = handlers.get(text)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_find_event_chat: {chat.current_step}")
