import logging
import uuid
from datetime import datetime

import psycopg
from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import (
    FlexMessage,
    Message,
    TemplateMessage,
    TextMessage,
)
from linebot.v3.webhooks import PostbackEvent

from routine_bot import messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.db import chats as chat_db
from routine_bot.db import events as event_db
from routine_bot.db import updates as update_db
from routine_bot.db import users as user_db
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import NewEventSteps
from routine_bot.enums.units import CycleUnit
from routine_bot.models import ChatData, EventData, UpdateData
from routine_bot.utils import format_logger_name, parse_event_cycle, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name_input(text: str, chat: ChatData, conn: psycopg.Connection) -> TextMessage | TemplateMessage:
    logger.info("Processing new event name input")
    event_name = text

    # validate event name
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name input: {event_name}")
        return TextMessage(text=error_msg)
    if event_db.get_event_id(chat.user_id, event_name, conn) is not None:
        logger.info(f"Duplicated event name input: {event_name}")
        return msg.info.event_name_duplicated(event_name)

    chat.payload["event_name"] = event_name
    chat.payload["chat_id"] = chat.chat_id
    chat.current_step = NewEventSteps.SELECT_START_DATE.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Added to payload: event_name={event_name}")
    logger.info(f"Added to payload: chat_id={chat.chat_id}")
    logger.info(f"Current step updated: {chat.current_step}")
    return msg.events.new.select_start_date(chat.payload)


# this function is called by handle_postback in handlers/main.py
def process_new_event_start_date_selection(
    postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection
) -> TemplateMessage:
    logger.info("Processing start date selection")
    if postback.postback.params is None:
        raise AttributeError("Postback cnotains no data")

    start_date = datetime.strptime(postback.postback.params["date"], "%Y-%m-%d")
    start_date = start_date.replace(tzinfo=TZ_TAIPEI)
    chat.payload["start_date"] = start_date.isoformat()  # datetime is not JSON serializable
    chat.current_step = NewEventSteps.ENABLE_REMINDER
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Added to payload: start_date={chat.payload['start_date']}")
    logger.info(f"Current step updated: {chat.current_step}")
    return msg.events.new.enable_reminder(chat.payload)


def _process_enable_reminder(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Processing enable reminder")
    chat.payload["reminder_enabled"] = "True"
    chat.current_step = NewEventSteps.SELECT_EVENT_CYCLE.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info("Added to payload: reminder_enabled=True")
    logger.info(f"Current step updated: {chat.current_step}")
    return msg.events.new.select_event_cycle(chat.payload)


def _process_disable_reminder(chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    logger.info("Processing disable reminder")
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
    logger.info("┌── New Event Created ──────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info("└───────────────────────────────────────────")

    update = UpdateData(
        update_id=str(uuid.uuid4()),
        event_id=event_id,
        event_name=chat.payload["event_name"],
        user_id=chat.user_id,
        done_at=datetime.fromisoformat(chat.payload["start_date"]),
    )
    update_db.add_update(update, conn)
    user_db.increment_user_event_count(chat.user_id, by=1, conn=conn)

    chat.payload["reminder_enabled"] = "False"
    chat.current_step = None
    chat.status = ChatStatus.COMPLETED.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    chat_db.set_chat_status(chat.chat_id, chat.status, conn)
    logger.info("Added to payload: reminder_enabled=False")
    logger.info(f"Current step updated: {chat.current_step}")
    logger.info("Chat completed")
    return msg.events.new.event_created_no_reminder(chat.payload)


def _process_event_cycle_input(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage | TemplateMessage:
    logger.info("Processing event cycle input")
    if text.lower() == "example":
        logger.info("Showing event cycle example")
        return msg.events.new.event_cycle_example()
    increment, unit = parse_event_cycle(text)
    if increment is None or unit is None:
        logger.info(f"Invalid event cycle input: {text}")
        return msg.events.new.invalid_input_for_event_cycle(chat.payload)
    chat.payload["event_cycle"] = text
    start_date = datetime.fromisoformat(chat.payload["start_date"])

    offset = relativedelta()
    if unit == CycleUnit.DAY:
        offset = relativedelta(days=+increment)
    elif unit == CycleUnit.WEEK:
        offset = relativedelta(weeks=+increment)
    elif unit == CycleUnit.MONTH:
        offset = relativedelta(months=+increment)
    next_due_at = start_date + offset

    chat.payload["next_due_at"] = next_due_at.isoformat()
    chat.current_step = None
    chat.status = ChatStatus.COMPLETED.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    chat_db.set_chat_status(chat.chat_id, chat.status, conn)
    logger.info(f"Added to payload: next_due_at={next_due_at}")
    logger.info(f"Current step updated: {chat.current_step}")
    logger.info("Chat completed")

    event_id = str(uuid.uuid4())
    event = EventData(
        event_id=event_id,
        user_id=chat.user_id,
        event_name=chat.payload["event_name"],
        reminder_enabled=True,
        event_cycle=chat.payload["event_cycle"],
        last_done_at=start_date,
        next_due_at=next_due_at,
        share_count=0,
        is_active=True,
    )
    event_db.add_event(event, conn)
    logger.info("┌── New Event Created ──────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Cycle: {event.event_cycle}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info(f"│ Next Due: {event.next_due_at}")
    logger.info("└───────────────────────────────────────────")

    update = UpdateData(
        update_id=str(uuid.uuid4()),
        event_id=event_id,
        event_name=chat.payload["event_name"],
        user_id=chat.user_id,
        done_at=datetime.fromisoformat(chat.payload["start_date"]),
    )
    update_db.add_update(update, conn)
    user_db.increment_user_event_count(chat.user_id, by=1, conn=conn)
    return msg.events.new.event_created_with_reminder(chat.payload)


def create_new_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage | TextMessage:
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
        current_step=NewEventSteps.INPUT_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.new.prompt_for_event_name()


def handle_new_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == NewEventSteps.INPUT_NAME:
        return _process_event_name_input(text, chat, conn)
    elif chat.current_step == NewEventSteps.SELECT_START_DATE:
        logger.info("Text input is not expected at current step")
        return msg.events.new.invalid_input_for_start_date(chat.payload)
    elif chat.current_step == NewEventSteps.ENABLE_REMINDER:
        if text == "設定提醒":
            return _process_enable_reminder(chat, conn)
        elif text == "不設定提醒":
            return _process_disable_reminder(chat, conn)
        else:
            logger.info(f"Invalid enable reminder input: {text}")
            return msg.events.new.invalid_input_for_enable_reminder(chat.payload)
    elif chat.current_step == NewEventSteps.SELECT_EVENT_CYCLE:
        return _process_event_cycle_input(text, chat, conn)
    else:
        logger.error(f"Unexpected step in handle_new_event_chat: {chat.current_step}")
        return msg.error.unexpected_error()
