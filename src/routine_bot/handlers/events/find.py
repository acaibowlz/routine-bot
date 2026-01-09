import logging
import uuid
from datetime import UTC, datetime

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
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData
from routine_bot.utils import get_time_diff, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing event name")
    event_name = text
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        cxt_logger.debug("Invalid event name: %r, error msg=%s", event_name, "".join(error_msg))
        return msg.error.error(error_msg)
    user_id = chat.user_id
    event = event_db.get_event_by_name(user_id, event_name, conn)
    if event is None:
        cxt_logger.debug("Event not found: user_id=%s, event_name=%r", user_id, event_name)
        return msg.error.event_name_not_found(event_name)
    cxt_logger.debug("Event found: event_name=%r, event_id=%s, user_id=%s", event_name, event.event_id, user_id)

    payload = {}
    payload["event_name"] = event_name
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
    recent_records = record_db.list_event_recent_records(event.event_id, conn)
    recent_records = [t.astimezone(tz=TZ_TAIPEI).strftime("%Y-%m-%d") for t in recent_records]
    payload["recent_records"] = recent_records
    chat.payload = chat_db.patch_chat_payload(chat=chat, new_data=payload, conn=conn, logger=logger)
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── Event Info ────────────────────────────",
            f"│ Event Name: {event_name}",
            f"│ Event ID: {event.event_id}",
            f"│ User: {chat.user_id}",
            f"│ Reminder: {event.reminder_enabled}",
            f"│ Cycle: {event.event_cycle}",
            f"│ Last Done: {event.last_done_at}",
            f"│ Next Due: {event.next_due_at.astimezone(UTC) if event.next_due_at else None}",
            f"│ Recent Records: {len(recent_records)}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info(f"Event info retrieved successfully\n{indent(summary)}")
    return msg.events.find.format_event_info(chat.payload)


def create_find_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=find_event", shorten_uuid(user_id))
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
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing find event chat: step=%s, text=%r", chat.current_step, text)
    handlers = {FindEventSteps.ENTER_NAME.value: _process_event_name}
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_find_event_chat: {chat.current_step}")
