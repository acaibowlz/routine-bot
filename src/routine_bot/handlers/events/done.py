import logging
import uuid
from datetime import UTC, datetime

import psycopg
from linebot.v3.messaging import TextMessage
from linebot.v3.webhooks import PostbackEvent

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.records as record_db
import routine_bot.messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import DoneEventSteps
from routine_bot.models import ChatData, RecordData
from routine_bot.utils import format_logger_name, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name_input(text: str, chat: ChatData, conn: psycopg.Connection):
    logger.info("Processing done event at name input")
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

    chat.payload["event_id"] = event_id
    chat.payload["event_name"] = event_name
    chat.payload["chat_id"] = chat.chat_id
    chat.current_step = DoneEventSteps.SELECT_DONE_DATE.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Adding to payload: event_id={chat.payload['event_id']}")
    logger.info(f"Adding to payload: event_name={chat.payload['event_name']}")
    logger.info(f"Adding to payload: chat_id={chat.payload['chat_id']}")
    logger.info(f"Setting current_step={chat.current_step}")
    return msg.events.done.select_done_at(chat.payload)


# this function is called by handle_postback in handlers/main.py
def process_done_date_selection(postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection):
    logger.info("Processing done date selection")
    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")

    done_at = datetime.strptime(postback.postback.params["date"], "%Y-%m-%d")
    done_at = done_at.replace(tzinfo=TZ_TAIPEI)
    logger.debug(f"Date received: {done_at}")
    if done_at > datetime.today().astimezone(tz=TZ_TAIPEI):
        logger.debug("Date exceeds today")
        return msg.events.done.invalid_selection_for_done_at_exceeds_today(chat.payload)

    event_id = chat.payload["event_id"]
    event = event_db.get_event(event_id, conn)
    assert event is not None, "Event is not suppose to be missing"
    record_id = str(uuid.uuid4())
    record = RecordData(
        record_id=record_id,
        event_id=event_id,
        event_name=event.event_name,
        user_id=chat.user_id,
        done_at=done_at,
    )
    record_db.add_record(record, conn)
    logger.info("┌── Creating New Record ────────────────────")
    logger.info(f"│ ID: {record_id}")
    logger.info(f"│ User: {chat.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Done At: {done_at.astimezone(UTC)}")
    logger.info("└───────────────────────────────────────────")
    if done_at > event.last_done_at:
        event_db.set_event_last_done_at(event_id, done_at, conn)

    chat.payload["done_at"] = done_at.isoformat()
    chat.current_step = None
    chat.status = ChatStatus.COMPLETED.value
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    chat_db.set_chat_status(chat.chat_id, chat.status, conn)
    logger.info(f"Setting current_step={chat.current_step}")
    logger.info(f"Finishing chat: {chat.chat_id}")
    return msg.events.done.succeeded(chat.payload)


def create_done_event_chat(user_id: str, conn: psycopg.Connection) -> TextMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: done event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.DONE_EVENT.value,
        current_step=DoneEventSteps.INPUT_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.done.prompt_for_event_name()


def handle_done_event_chat(text: str, chat: ChatData, conn: psycopg.Connection):
    if chat.current_step == DoneEventSteps.INPUT_NAME:
        return _process_event_name_input(text, chat, conn)
    elif chat.current_step == DoneEventSteps.SELECT_DONE_DATE:
        logger.info("Text input is not expected at current step")
        return msg.events.done.invalid_input_for_done_at(chat.payload)
    else:
        raise AssertionError(f"Unknown step in handle_update_done_at_chat: {chat.current_step}")
