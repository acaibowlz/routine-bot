import logging
import uuid
from datetime import UTC, datetime

import psycopg
from linebot.v3.messaging import FlexMessage, TemplateMessage
from linebot.v3.webhooks import PostbackEvent

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.records as record_db
import routine_bot.messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import DoneEventSteps
from routine_bot.errors import EventNotFoundError, InvalidStepError
from routine_bot.models import ChatData, RecordData
from routine_bot.utils import format_logger_name, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing event name")
    event_name = text
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name. Input: {event_name}, Error msg: {''.join(error_msg)}")
        return msg.error.error(error_msg)
    event_id = event_db.get_event_id(chat.user_id, event_name, conn)
    if event_id is None:
        logger.info(f"Event not found: {event_name}")
        return msg.error.event_name_not_found(event_name)

    chat_db.set_chat_current_step(chat.chat_id, DoneEventSteps.SELECT_DONE_DATE.value, conn)
    chat.payload = chat_db.update_chat_payload(
        chat=chat,
        new_data={"event_id": event_id, "event_name": event_name, "chat_id": chat.chat_id},
        conn=conn,
        logger=logger,
    )
    return msg.events.done.select_done_at(chat.payload)


# this function is called by handle_postback in handlers/main.py
def process_selected_done_date(
    postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection
) -> TemplateMessage | FlexMessage:
    logger.info("Processing selected done date")
    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")

    done_at = datetime.strptime(postback.postback.params["date"], "%Y-%m-%d")
    done_at = done_at.replace(tzinfo=TZ_TAIPEI)
    logger.info(f"Selected done date: {done_at}")
    if done_at > datetime.today().astimezone(tz=TZ_TAIPEI):
        logger.info("Date exceeds today")
        return msg.events.done.invalid_done_date_selected_exceeds_today(chat.payload)

    event_id = chat.payload["event_id"]
    event = event_db.get_event_by_id(event_id, conn)
    if event is None:
        raise EventNotFoundError(f"Event not found: {event_id}")
    record_id = str(uuid.uuid4())
    record = RecordData(
        record_id=record_id,
        event_id=event_id,
        event_name=event.event_name,
        user_id=chat.user_id,
        done_at=done_at,
    )
    logger.info("┌── Creating New Record ────────────────────")
    logger.info(f"│ ID: {record_id}")
    logger.info(f"│ User: {chat.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Done At: {done_at.astimezone(UTC)}")
    logger.info("└───────────────────────────────────────────")
    record_db.add_record(record, conn)

    if done_at > event.last_done_at:
        logger.info("Updating event's last done date: The new done date is more recent")
        event_db.set_event_last_done_at(event_id, done_at, conn)

    chat_db.finish_chat(chat, conn, logger)
    chat.payload = chat_db.update_chat_payload(
        chat=chat,
        new_data={"done_at": done_at.isoformat()},
        conn=conn,
        logger=logger,
    )
    return msg.events.done.succeeded(chat.payload)


def create_done_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: done event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.DONE_EVENT.value,
        current_step=DoneEventSteps.ENTER_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.done.enter_event_name()


def handle_done_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    if chat.current_step == DoneEventSteps.ENTER_NAME:
        return _process_event_name(text, chat, conn)
    elif chat.current_step == DoneEventSteps.SELECT_DONE_DATE:
        logger.info("Text input is not expected at current step")
        return msg.events.done.invalid_input_for_done_at(chat.payload)
    else:
        raise InvalidStepError(f"Invalid step in handle_update_done_at_chat: {chat.current_step}")
