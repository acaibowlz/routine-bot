import logging
import uuid
from datetime import UTC

import psycopg
from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import TemplateMessage
from linebot.v3.messaging.models.flex_message import FlexMessage

from routine_bot import messages as msg
from routine_bot.db import chats as chat_db
from routine_bot.db import events as event_db
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.options import EditEventOptions, ToggleReminderOptions
from routine_bot.enums.steps import EditEventSteps
from routine_bot.enums.units import CycleUnit
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, parse_event_cycle, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name_entry(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing edit event name input")
    event_name = text

    # validate event name
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name input: {event_name}")
        logger.debug(f"Error msg={error_msg}")
        return msg.error.error([error_msg])
    event_id = event_db.get_event_id(chat.user_id, event_name, conn)
    if event_id is None:
        logger.info(f"Event not found: {event_name}")
        return msg.error.event_name_not_found(event_name)

    event = event_db.get_event(event_id, conn)
    assert event is not None, "Event is not suppose to be missing"
    chat_db.update_chat_current_step(chat, EditEventSteps.SELECT_OPTION.value, conn, logger)
    new_payload = chat_db.update_chat_payload(
        chat=chat,
        data={
            "event_name": event_name,
            "event_id": event_id,
            "last_done_at": event.last_done_at.isoformat(),
            "reminder_enabled": str(event.reminder_enabled),
            "event_cycle": event.event_cycle if event.event_cycle else "None",
        },
        conn=conn,
        logger=logger,
    )
    return msg.events.edit.select_option(new_payload)


def _prepare_new_event_name_entry(chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    chat_db.update_chat_current_step(chat, EditEventSteps.ENTER_NEW_NAME.value, conn, logger)
    return msg.events.edit.enter_new_event_name(chat.payload)


def _prepare_toggle_reminder(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    chat_db.update_chat_current_step(chat, EditEventSteps.TOGGLE_REMINDER.value, conn, logger)
    return msg.events.edit.toggle_reminder(chat.payload)


def _prepare_new_event_cycle_entry(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    chat_db.update_chat_current_step(chat, EditEventSteps.ENTER_NEW_EVENT_CYCLE.value, conn, logger)
    return msg.events.edit.enter_new_event_cycle(chat.payload)


def _process_selected_edit_option(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing selected edit option")
    if text == EditEventOptions.NAME:
        return _prepare_new_event_name_entry(chat, conn)
    elif text == EditEventOptions.REMINDER:
        return _prepare_toggle_reminder(chat, conn)
    elif text == EditEventOptions.EVENT_CYCLE:
        if chat.payload["reminder_enabled"] == "False":
            logger.info("Event cycle cannot be set if reminder is not enabled")
            return msg.events.edit.event_cycle_requires_reminder_enabled(chat.payload)
        return _prepare_new_event_cycle_entry(chat, conn)
    else:
        logger.info(f"Invalid edit option input: {text}")
        return msg.events.edit.invalid_edit_option_entry(chat.payload)


def _process_new_event_name_entry(text: str, chat: ChatData, conn: psycopg.Connection):
    logger.info("Processing edit event new name entry")
    new_event_name = text

    # validate event name
    error_msg = validate_event_name(new_event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name entry: {new_event_name}, error msg={error_msg}")
        return msg.error.error([error_msg])
    if event_db.get_event_id(chat.user_id, new_event_name, conn) is not None:
        logger.info(f"Duplicated event name entry: {new_event_name}")
        return msg.error.event_name_duplicated(new_event_name)

    event = event_db.get_event(chat.payload["event_id"], conn)
    assert event is not None, "Event is not suppose to be missing"
    logger.info("┌── Editing Event ──────────────────────────")
    logger.info(f"│ Event Name: {event.event_name}")
    logger.info(f"│ Event ID: {event.event_id}")
    logger.info(f"│ User: {chat.user_id}")
    logger.info(f"│ New Event Name: {new_event_name}")
    logger.info("└───────────────────────────────────────────")
    event_db.set_event_name(event.event_id, new_event_name, conn)

    chat_db.finish_chat(chat, conn, logger)
    new_payload = chat_db.update_chat_payload(
        chat=chat, data={"new_event_name": new_event_name}, conn=conn, logger=logger
    )
    return msg.events.edit.edit_event_name_succeeded(new_payload)


def _process_toggle_reminder(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing edit event toggle reminder")
    if text == ToggleReminderOptions.CANCEL:
        logger.info("Cancelling toggle reminder")
        chat_db.finish_chat(chat, conn, logger)
        return msg.events.edit.toggle_reminder_cancelled(chat.payload)

    elif text == ToggleReminderOptions.CONFIRM:
        logger.info("Toggling reminder")
        new_reminder_flag = False if chat.payload["reminder_enabled"] == "True" else True

        if new_reminder_flag and chat.payload["event_cycle"] == "None":
            logger.info("Event cycle is missing, proceed to set event cycle")
            chat_db.update_chat_current_step(chat, EditEventSteps.ENTER_NEW_EVENT_CYCLE.value, conn, logger)
            new_payload = chat_db.update_chat_payload(
                chat=chat, data={"proceed_from_toggle_reminder": str(True)}, conn=conn, logger=logger
            )
            return msg.events.edit.proceed_to_set_event_cycle(new_payload)

        event = event_db.get_event(chat.payload["event_id"], conn)
        assert event is not None, "Event is not suppose to be missing"
        logger.info("┌── Editing Event ──────────────────────────")
        logger.info(f"│ Event Name: {event.event_name}")
        logger.info(f"│ Event ID: {event.event_id}")
        logger.info(f"│ User: {chat.user_id}")
        logger.info(f"│ New Reminder Flag: {new_reminder_flag}")
        logger.info("└───────────────────────────────────────────")
        event_db.set_event_reminder_flag(event.event_id, new_reminder_flag, conn)
        chat_db.finish_chat(chat, conn, logger)
        return msg.events.edit.toggle_reminder_succeeded(chat.payload)

    else:
        logger.info(f"Invalid edit option input: {text}")
        return msg.events.edit.invalid_toggle_reminder_entry(chat.payload)


def _process_new_event_cycle_entry(
    text: str, chat: ChatData, conn: psycopg.Connection
) -> TemplateMessage | FlexMessage:
    logger.info("Processing edit event new event cycle entry")
    if text.lower() == "example":
        logger.info("Showing event cycle example")
        return msg.info.event_cycle_example()

    # remove plural form
    text = text.rstrip("s")
    increment, unit = parse_event_cycle(text)
    if increment is None or unit is None:
        logger.info(f"Invalid event cycle entry: {text}")
        return msg.events.edit.invalid_event_cycle_entry(chat.payload)

    event = event_db.get_event(chat.payload["event_id"], conn)
    assert event is not None, "Event is not suppose to be missing"
    event_id = event.event_id
    last_done_at = event.last_done_at
    offset = relativedelta()
    if unit == CycleUnit.DAY:
        offset = relativedelta(days=+increment)
    elif unit == CycleUnit.WEEK:
        offset = relativedelta(weeks=+increment)
    elif unit == CycleUnit.MONTH:
        offset = relativedelta(months=+increment)
    next_due_at = last_done_at + offset
    new_event_cycle = f"{increment} {unit}"
    logger.info("┌── Editing Event ──────────────────────────")
    logger.info(f"│ Event Name: {event.event_name}")
    logger.info(f"│ Event ID: {event_id}")
    logger.info(f"│ User: {chat.user_id}")
    logger.info(f"│ Last Done: {last_done_at.astimezone(UTC)}")
    logger.info(f"│ New Cycle: {new_event_cycle}")
    logger.info(f"│ Next Due: {next_due_at.astimezone(UTC)}")
    logger.info("└───────────────────────────────────────────")
    event_db.set_event_cycle(event_id, new_event_cycle, conn)
    event_db.set_event_next_due_at(event_id, next_due_at, conn)

    if chat.payload.get("proceed_from_toggle_reminder"):
        logger.info("Event is proceeded from toggle reminder, setting new reminder flag")
        event_db.set_event_reminder_flag(event_id, True, conn)

    chat_db.finish_chat(chat, conn, logger)
    new_payload = chat_db.update_chat_payload(
        chat=chat,
        data={"new_event_cycle": new_event_cycle, "next_due_at": next_due_at.isoformat()},
        conn=conn,
        logger=logger,
    )
    if new_payload.get("proceed_from_toggle_reminder"):
        return msg.events.edit.toggle_reminder_succeeded(new_payload)
    return msg.events.edit.edit_event_cycle_succeeded(new_payload)


def create_edit_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: edit event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.EDIT_EVENT.value,
        current_step=EditEventSteps.ENTER_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.edit.enter_event_name()


def handle_edit_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    if chat.current_step == EditEventSteps.ENTER_NAME:
        return _process_event_name_entry(text, chat, conn)
    elif chat.current_step == EditEventSteps.SELECT_OPTION:
        return _process_selected_edit_option(text, chat, conn)
    elif chat.current_step == EditEventSteps.ENTER_NEW_NAME:
        return _process_new_event_name_entry(text, chat, conn)
    elif chat.current_step == EditEventSteps.TOGGLE_REMINDER:
        return _process_toggle_reminder(text, chat, conn)
    elif chat.current_step == EditEventSteps.ENTER_NEW_EVENT_CYCLE:
        return _process_new_event_cycle_entry(text, chat, conn)
    else:
        raise AssertionError(f"Unknown step in handle_edit_event_chat: {chat.current_step}")
