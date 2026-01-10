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
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData, RecordData
from routine_bot.utils import validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing event name")
    event_name = text

    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        cxt_logger.debug("Invalid event name: %r, error msg=%s", event_name, "".join(error_msg))
        return msg.error.error(error_msg)
    user_id = chat.user_id
    event_id = event_db.get_event_id(user_id, event_name, conn)
    if event_id is None:
        cxt_logger.debug("Event not found: user_id=%s, event_name=%r", user_id, event_name)
        return msg.error.event_name_not_found(event_name)

    cxt_logger.info("Event selected: %r (%s)", event_name, shorten_uuid(event_id))
    chat_db.set_chat_current_step(chat.chat_id, DoneEventSteps.SELECT_DONE_DATE.value, conn)
    chat.payload = chat_db.patch_chat_payload(
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
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing new done date")
    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")

    done_at = datetime.strptime(postback.postback.params["date"], "%Y-%m-%d")
    done_at = done_at.replace(tzinfo=TZ_TAIPEI)

    event_id = chat.payload["event_id"]
    event = event_db.get_event_by_id(event_id, conn)
    today = datetime.today().astimezone(tz=TZ_TAIPEI)
    if done_at > today:
        cxt_logger.debug("Done date exceeds today: %s > %s", done_at.astimezone(UTC), today.astimezone(UTC))
        return msg.events.done.invalid_done_date_selected_exceeds_today(chat.payload)

    record_id = str(uuid.uuid4())
    record = RecordData(
        record_id=record_id,
        event_id=event_id,
        event_name=event.event_name,
        user_id=chat.user_id,
        done_at=done_at,
    )
    record_db.add_record(record, conn)
    cxt_logger.info(f"New done date set to {done_at.astimezone(UTC)}")
    if done_at > event.last_done_at:
        logger.info("Updating event's latest done date")
        event_db.set_event_last_done_at(event_id, done_at, conn)

    summary = "\n".join(
        [
            "┌── New Record ─────────────────────────────",
            f"│ Record ID: {record_id}",
            f"│ User: {event.user_id}",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event_id}",
            f"│ New Done Date: {done_at.astimezone(UTC)}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Record created successfully\n%s", indent(summary))

    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"done_at": done_at.isoformat()},
        conn=conn,
        logger=logger,
    )
    chat_db.finalize_chat(chat, conn, logger)
    return msg.events.done.succeeded(chat.payload)


def create_done_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=done_event", shorten_uuid(user_id))
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
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing done event chat: step=%s, text=%r", chat.current_step, text)
    handlers = {
        DoneEventSteps.ENTER_NAME.value: _process_event_name,
        DoneEventSteps.SELECT_DONE_DATE.value: lambda text, chat, conn: msg.events.done.invalid_text_input(
            chat.payload
        ),
    }
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_update_done_at_chat: {chat.current_step}")
