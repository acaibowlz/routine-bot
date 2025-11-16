import logging
import uuid
from datetime import UTC, datetime

import psycopg
from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import FlexMessage, TemplateMessage, TextMessage
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
from routine_bot.models import ChatData, EventData, RecordData
from routine_bot.utils import format_logger_name, parse_event_cycle, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name_entry(text: str, chat: ChatData, conn: psycopg.Connection) -> TextMessage | TemplateMessage:
    logger.info("Processing new event name entry")
    event_name = text

    # validate event name
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name entry: {event_name}, error msg={error_msg}")
        return TextMessage(text=error_msg)
    if event_db.get_event_id(chat.user_id, event_name, conn) is not None:
        logger.info(f"Duplicated event name entry: {event_name}")
        return msg.info.event_name_duplicated(event_name)

    chat.payload["event_name"] = event_name
    chat.payload["chat_id"] = chat.chat_id
    logger.debug(f"Adding to payload: event_name={event_name}")
    logger.debug(f"Adding to payload: chat_id={chat.chat_id}")
    logger.info(f"Setting current_step={chat.current_step}")
    chat.current_step = NewEventSteps.SELECT_START_DATE.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    return msg.events.new.select_start_date(chat.payload)


# this function is called by handle_postback in handlers/main.py
def process_selected_start_date(postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Processing selected start date")
    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")

    start_date = datetime.strptime(postback.postback.params["date"], "%Y-%m-%d")
    start_date = start_date.replace(tzinfo=TZ_TAIPEI)
    logger.debug(f"Selected start date: {start_date}")
    if start_date > datetime.today().astimezone(tz=TZ_TAIPEI):
        logger.debug("Start date exceeds today")
        return msg.events.new.invalid_start_date_selected_exceeds_today(chat.payload)

    chat.payload["start_date"] = start_date.isoformat()
    chat.current_step = NewEventSteps.ENTER_REMINDER_OPTION.value
    logger.debug(f"Adding to payload: start_date={chat.payload['start_date']}")
    logger.info(f"Setting current_step={chat.current_step}")
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    return msg.events.new.enable_reminder(chat.payload)


def _process_reminder_enabled(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Reminder is enabled")
    chat.current_step = NewEventSteps.ENTER_EVENT_CYCLE.value
    logger.info(f"Setting current_step={chat.current_step}")
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    return msg.events.new.select_event_cycle(chat.payload)


def _process_reminder_disabled(chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    logger.info("Reminder is disabled")
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
    logger.info("┌── Creating New Event ─────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Last Done: {event.last_done_at.astimezone(UTC)}")
    logger.info("└───────────────────────────────────────────")
    event_db.add_event(event, conn)

    record = RecordData(
        record_id=str(uuid.uuid4()),
        event_id=event_id,
        event_name=chat.payload["event_name"],
        user_id=chat.user_id,
        done_at=datetime.fromisoformat(chat.payload["start_date"]),
    )
    record_db.add_record(record, conn)
    user_db.increment_user_event_count(chat.user_id, by=1, conn=conn)

    chat.current_step = None
    chat.status = ChatStatus.COMPLETED.value
    logger.info(f"Setting current_step={chat.current_step}")
    logger.info(f"Finishing chat: {chat.chat_id}")
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    chat_db.set_chat_status(chat.chat_id, chat.status, conn)
    return msg.events.new.succeeded_no_reminder(chat.payload)


def _process_selected_reminder_option(
    text: str, chat: ChatData, conn: psycopg.Connection
) -> TemplateMessage | FlexMessage:
    logger.info("Processing reminder option entry")
    if text == NewEventReminderOptions.ENABLE:
        return _process_reminder_enabled(chat, conn)
    elif text == NewEventReminderOptions.DISABLE:
        return _process_reminder_disabled(chat, conn)
    else:
        logger.info(f"Invalid enable reminder input: {text}")
        return msg.events.new.invalid_entry_for_enable_reminder(chat.payload)


def _process_event_cycle_entry(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing event cycle entry")
    if text.lower() == "example":
        logger.info("Showing event cycle example")
        return msg.info.event_cycle_example()

    # remove plural form
    text = text.rstrip("s")
    increment, unit = parse_event_cycle(text)
    if increment is None or unit is None:
        logger.info(f"Invalid event cycle entry: {text}")
        return msg.events.new.invalid_entry_for_event_cycle(chat.payload)

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
    assert event.next_due_at is not None, "Next due date should be set at this step"
    logger.info("┌── Creating New Event ─────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Cycle: {event.event_cycle}")
    logger.info(f"│ Last Done: {event.last_done_at.astimezone(UTC)}")
    logger.info(f"│ Next Due: {event.next_due_at.astimezone(UTC)}")
    logger.info("└───────────────────────────────────────────")
    event_db.add_event(event, conn)

    update = RecordData(
        record_id=str(uuid.uuid4()),
        event_id=event_id,
        event_name=chat.payload["event_name"],
        user_id=chat.user_id,
        done_at=datetime.fromisoformat(chat.payload["start_date"]),
    )
    record_db.add_record(update, conn)
    user_db.increment_user_event_count(chat.user_id, by=1, conn=conn)

    chat.payload["event_cycle"] = text
    chat.payload["next_due_at"] = next_due_at.isoformat()
    chat.current_step = None
    chat.status = ChatStatus.COMPLETED.value
    logger.debug(f"Adding to payload: event_cycle={chat.payload['event_cycle']}")
    logger.debug(f"Adding to payload: next_due_at={chat.payload['next_due_at']}")
    logger.info(f"Setting current_step={chat.current_step}")
    logger.info(f"Finishing chat: {chat.chat_id}")
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    chat_db.set_chat_status(chat.chat_id, chat.status, conn)
    return msg.events.new.succeeded_with_reminder(chat.payload)


def create_new_event_chat(user_id: str, conn: psycopg.Connection) -> TextMessage | FlexMessage:
    user = user_db.get_user(user_id, conn)
    if user is None:
        raise ValueError(f"User not found: {user_id}")
    if user.is_limited:
        logger.info("Failed to create new event: reached max events allowed")
        return msg.info.max_events_reached()
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: new event")
    logger.info(f"Chat ID: {chat_id}")
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


def handle_new_event_chat(
    text: str, chat: ChatData, conn: psycopg.Connection
) -> TextMessage | TemplateMessage | FlexMessage:
    if chat.current_step == NewEventSteps.ENTER_NAME:
        return _process_event_name_entry(text, chat, conn)
    elif chat.current_step == NewEventSteps.SELECT_START_DATE:
        logger.info("Text input is not expected at current step")
        return msg.events.new.invalid_entry_for_start_date(chat.payload)
    elif chat.current_step == NewEventSteps.ENTER_REMINDER_OPTION:
        return _process_selected_reminder_option(text, chat, conn)
    elif chat.current_step == NewEventSteps.ENTER_EVENT_CYCLE:
        return _process_event_cycle_entry(text, chat, conn)
    else:
        raise AssertionError(f"Unknown step in handle_new_event_chat: {chat.current_step}")
