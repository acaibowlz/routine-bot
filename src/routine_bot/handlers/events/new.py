import logging
import uuid
from datetime import UTC, datetime

import psycopg
from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import FlexMessage, TemplateMessage
from linebot.v3.webhooks import PostbackEvent

from routine_bot import messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.db import chats as chat_db
from routine_bot.db import events as event_db
from routine_bot.db import records as record_db
from routine_bot.db import users as user_db
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.options import NewEventReminderOptions
from routine_bot.enums.steps import NewEventSteps
from routine_bot.enums.units import CycleUnit
from routine_bot.errors import InvalidStepError
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData, EventData, RecordData
from routine_bot.utils import parse_event_cycle, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing event name")
    event_name = text
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        cxt_logger.debug("Invalid event name: %r, error msg=%s", event_name, "".join(error_msg))
        return msg.error.error(error_msg)
    if event_db.is_event_name_duplicated(chat.user_id, event_name, conn):
        cxt_logger.debug("Duplicated event name: %r", event_name)
        return msg.error.event_name_dupliclicated(event_name)

    cxt_logger.info("Event name set to %r", event_name)
    chat_db.set_chat_current_step(chat.chat_id, NewEventSteps.SELECT_START_DATE.value, conn)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"event_name": event_name, "chat_id": chat.chat_id},
        conn=conn,
        logger=logger,
    )
    return msg.events.new.select_start_date(chat.payload)


# this function is called by handle_postback in handlers/main.py
def process_selected_start_date(postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing selected start date")
    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")

    start_date = datetime.strptime(postback.postback.params["date"], "%Y-%m-%d")
    start_date = start_date.replace(tzinfo=TZ_TAIPEI)
    today = datetime.today().astimezone(tz=TZ_TAIPEI)
    cxt_logger.info("Start date set to %s", start_date.astimezone(UTC))
    if start_date > today:
        cxt_logger.debug("Start date exceeds today: %s > %s", start_date.astimezone(UTC), today.astimezone(UTC))
        return msg.events.new.invalid_start_date_selected_exceeds_today(chat.payload)

    chat_db.set_chat_current_step(chat.chat_id, NewEventSteps.ENTER_REMINDER_OPTION.value, conn)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"start_date": start_date.isoformat()},
        conn=conn,
        logger=logger,
    )
    return msg.events.new.enable_reminder(chat.payload)


def _process_enabling_reminder(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.info("Reminder enabled")
    chat_db.set_chat_current_step(chat.chat_id, NewEventSteps.ENTER_EVENT_CYCLE.value, conn)
    return msg.events.new.select_event_cycle(chat.payload)


def _process_disabling_reminder(chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.info("Reminder disabled")
    event_id = str(uuid.uuid4())
    event = EventData(
        event_id=event_id,
        user_id=chat.user_id,
        event_name=chat.payload["event_name"],
        reminder_enabled=False,
        event_cycle=None,
        last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
        next_due_at=None,
        share_count=0,
        is_active=True,
    )
    event_db.add_event(event, conn)
    user_db.increment_user_event_count(chat.user_id, by=1, conn=conn)

    record = RecordData(
        record_id=str(uuid.uuid4()),
        event_id=event_id,
        event_name=chat.payload["event_name"],
        user_id=chat.user_id,
        done_at=datetime.fromisoformat(chat.payload["start_date"]),
    )
    record_db.add_record(record, conn)
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── New Event ──────────────────────────────",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event_id}",
            f"│ User: {event.user_id}",
            f"│ Reminder: {event.reminder_enabled}",
            f"│ Last Done: {event.last_done_at.astimezone(UTC)}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Event created successfully\n%s", indent(summary))
    return msg.events.new.succeeded_no_reminder(chat.payload)


def _process_selected_reminder_option(
    text: str, chat: ChatData, conn: psycopg.Connection
) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing reminder option")
    handlers = {
        NewEventReminderOptions.ENABLE.value: _process_enabling_reminder,
        NewEventReminderOptions.DISABLE.value: _process_disabling_reminder,
    }
    handler = handlers.get(text)
    if handler:
        return handler(chat, conn)
    cxt_logger.debug("Invalid entry: %r", text)
    return msg.events.new.invalid_reminder_option(chat.payload)


def _process_event_cycle(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing event cycle")
    if text.lower() == "example":
        return msg.info.event_cycle_example()

    # remove plural form
    event_cycle = text.rstrip("s")
    increment, unit = parse_event_cycle(event_cycle)
    if increment is None or unit is None:
        cxt_logger.debug("Invalid event cycle: %r", event_cycle)
        return msg.events.new.invalid_event_cycle(chat.payload)
    cxt_logger.info("Event cycle set to %s %s", increment, unit)

    start_date = datetime.fromisoformat(chat.payload["start_date"])
    offset = relativedelta()
    if unit == CycleUnit.DAY:
        offset = relativedelta(days=+increment)
    elif unit == CycleUnit.WEEK:
        offset = relativedelta(weeks=+increment)
    elif unit == CycleUnit.MONTH:
        offset = relativedelta(months=+increment)
    next_due_at = start_date + offset

    event_id = str(uuid.uuid4())
    event = EventData(
        event_id=event_id,
        user_id=chat.user_id,
        event_name=chat.payload["event_name"],
        reminder_enabled=True,
        event_cycle=f"{increment} {unit}",
        last_done_at=start_date,
        next_due_at=next_due_at,
        share_count=0,
        is_active=True,
    )
    event_db.add_event(event, conn)
    user_db.increment_user_event_count(chat.user_id, by=1, conn=conn)

    update = RecordData(
        record_id=str(uuid.uuid4()),
        event_id=event_id,
        event_name=chat.payload["event_name"],
        user_id=chat.user_id,
        done_at=datetime.fromisoformat(chat.payload["start_date"]),
    )
    record_db.add_record(update, conn)

    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"event_cycle": event_cycle, "next_due_at": next_due_at.isoformat()},
        conn=conn,
        logger=logger,
    )
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── New Event ──────────────────────────────",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event_id}",
            f"│ User: {event.user_id}",
            f"│ Reminder: {event.reminder_enabled}",
            f"│ Event Cycle: {event.event_cycle}",
            f"│ Last Done: {event.last_done_at.astimezone(UTC)}",
            f"│ Next Due: {next_due_at.astimezone(UTC)}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Event created successfully\n%s", indent(summary))
    return msg.events.new.succeeded_with_reminder(chat.payload)


def create_new_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    if user_db.is_user_limited(user_id, conn):
        logger.info("Failed to create new event: user_id=%s exceeded free plan max event count", user_id)
        return msg.events.new.max_events_reached()
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=new_event", shorten_uuid(user_id))
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.NEW_EVENT.value,
        current_step=NewEventSteps.ENTER_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.new.enter_event_name()


def handle_new_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing new event chat: step=%s, text=%r", chat.current_step, text)
    handlers = {
        NewEventSteps.ENTER_NAME.value: _process_event_name,
        NewEventSteps.SELECT_START_DATE.value: lambda text, chat, conn: msg.events.new.invalid_text_input(chat.payload),
        NewEventSteps.ENTER_REMINDER_OPTION.value: _process_selected_reminder_option,
        NewEventSteps.ENTER_EVENT_CYCLE.value: _process_event_cycle,
    }
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_new_event_chat: {chat.current_step}")
