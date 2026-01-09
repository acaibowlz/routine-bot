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
from routine_bot.errors import InvalidStepError
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData
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
    user_id = chat.user_id
    event = event_db.get_event_by_name(user_id, event_name, conn)
    if event is None:
        cxt_logger.debug("Event not found: user_id=%s, event_name=%r", user_id, event_name)
        return msg.error.event_name_not_found(event_name)

    cxt_logger.info("Event selected: %r (%s)", event_name, shorten_uuid(event.event_id))
    chat_db.set_chat_current_step(chat.chat_id, EditEventSteps.SELECT_OPTION.value, conn)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={
            "event_name": event_name,
            "event_id": event.event_id,
            "last_done_at": event.last_done_at.isoformat(),
            "reminder_enabled": str(event.reminder_enabled),
            "event_cycle": event.event_cycle if event.event_cycle else "None",
        },
        conn=conn,
        logger=logger,
    )
    return msg.events.edit.select_option(chat.payload)


def _prepare_new_event_name(chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    chat_db.set_chat_current_step(chat.chat_id, EditEventSteps.ENTER_NEW_NAME.value, conn)
    return msg.events.edit.enter_new_event_name(chat.payload)


def _prepare_toggle_reminder(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    chat_db.set_chat_current_step(chat.chat_id, EditEventSteps.TOGGLE_REMINDER.value, conn)
    return msg.events.edit.toggle_reminder(chat.payload)


def _prepare_new_event_cycle(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    if chat.payload["reminder_enabled"] == "False":
        cxt_logger = add_context(logger, chat_id=chat.chat_id)
        cxt_logger.debug("Cannot edit event cycle if reminder is disabled")
        return msg.events.edit.event_cycle_requires_reminder_enabled(chat.payload)
    chat_db.set_chat_current_step(chat.chat_id, EditEventSteps.ENTER_NEW_EVENT_CYCLE.value, conn)
    return msg.events.edit.enter_new_event_cycle(chat.payload)


def _process_selected_edit_option(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing selected edit option")
    handlers = {
        EditEventOptions.NAME.value: _prepare_new_event_name,
        EditEventOptions.REMINDER.value: _prepare_toggle_reminder,
        EditEventOptions.EVENT_CYCLE.value: _prepare_new_event_cycle,
    }
    handler = handlers.get(text)
    if handler:
        cxt_logger.debug("Option selected: %r", text)
        return handler(chat, conn)
    cxt_logger.debug("Invalid entry: %r", text)
    return msg.events.edit.invalid_edit_option(chat.payload)


def _process_new_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing new event name")
    new_event_name = text
    error_msg = validate_event_name(new_event_name)
    if error_msg is not None:
        cxt_logger.debug("Invalid event name: %r, error msg=%s", new_event_name, "".join(error_msg))
        return msg.error.error(error_msg)
    if event_db.is_event_name_duplicated(chat.user_id, new_event_name, conn):
        cxt_logger.debug("Duplicated event name: %r", new_event_name)
        return msg.error.event_name_duplicated(new_event_name)

    event_id = chat.payload["event_id"]
    event = event_db.get_event_by_id(event_id, conn)
    event_db.set_event_name(event.event_id, new_event_name, conn)
    cxt_logger.info("Event name set to %r", new_event_name)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat, new_data={"new_event_name": new_event_name}, conn=conn, logger=logger
    )
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── Event Modified ─────────────────────────",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event.event_id}",
            f"│ User: {chat.user_id}",
            "│ Change: Event name",
            f"│ Details: {event.event_name} → {new_event_name}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Event modified successfully\n%s", indent(summary))
    return msg.events.edit.edit_event_name_succeeded(chat.payload)


def _cancel_toggle_reminder(chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Cancelled toggling reminder")
    chat_db.finalize_chat(chat, conn, logger)
    return msg.events.edit.toggle_reminder_cancelled(chat.payload)


def _confirm_toggle_reminder(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Confirmed toggling reminder")
    old_reminder_flag = chat.payload.get("reminder_enabled") == "True"
    new_reminder_flag = not old_reminder_flag

    if new_reminder_flag and chat.payload["event_cycle"] == "None":
        cxt_logger.info("Event cycle is missing, proceed to set event cycle")
        chat_db.set_chat_current_step(chat.chat_id, EditEventSteps.ENTER_NEW_EVENT_CYCLE.value, conn)
        chat.payload = chat_db.patch_chat_payload(
            chat=chat, new_data={"proceed_from_toggle_reminder": str(True)}, conn=conn, logger=logger
        )
        return msg.events.edit.proceed_to_set_event_cycle(chat.payload)

    event_id = chat.payload["event_id"]
    event = event_db.get_event_by_id(event_id, conn)
    event_db.set_event_reminder_enabled(event.event_id, new_reminder_flag, conn)
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── Event Modified ─────────────────────────",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event.event_id}",
            f"│ User: {chat.user_id}",
            "│ Change: Reminder",
            f"│ Details: {'enabled' if old_reminder_flag else 'disabled'} → "
            f"{'enabled' if new_reminder_flag else 'disabled'}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Event modified successfully\n%s", indent(summary))
    return msg.events.edit.toggle_reminder_succeeded(chat.payload)


def _process_toggle_reminder(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing toggle reminder")
    handlers = {
        ToggleReminderOptions.CANCEL.value: _cancel_toggle_reminder,
        ToggleReminderOptions.CONFIRM.value: _confirm_toggle_reminder,
    }
    handler = handlers.get(text)
    if handler:
        return handler(chat, conn)
    cxt_logger.debug("Invalid entry: %r", text)
    return msg.events.edit.invalid_toggle_reminder_entry(chat.payload)


def _process_new_event_cycle(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing new event cycle")
    if text.lower() == "example":
        cxt_logger.debug("Showing event cycle example")
        return msg.info.event_cycle_example()

    # remove plural form
    text = text.rstrip("s")
    increment, unit = parse_event_cycle(text)
    if increment is None or unit is None:
        cxt_logger.debug("Invalid event cycle: %r", text)
        return msg.events.edit.invalid_event_cycle_entry(chat.payload)

    event_id = chat.payload["event_id"]
    event = event_db.get_event_by_id(event_id, conn)
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

    if chat.payload.get("proceed_from_toggle_reminder"):
        event_db.set_event_reminder_enabled(event_id, True, conn)
    event_db.set_event_cycle(event_id, new_event_cycle, conn)
    event_db.set_event_next_due_at(event_id, next_due_at, conn)
    cxt_logger.info("Event cycle set to %s", new_event_cycle)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"new_event_cycle": new_event_cycle, "next_due_at": next_due_at.isoformat()},
        conn=conn,
        logger=logger,
    )
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── Event Modified ─────────────────────────",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event.event_id}",
            f"│ User: {chat.user_id}",
            "│ Change: Event cycle",
            f"│ Details: {event.event_cycle or 'None'} → {new_event_cycle}",
            f"│ Last Done: {last_done_at.astimezone(UTC)}",
            f"│ Next Due: {next_due_at.astimezone(UTC)}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Event modified successfully\n%s", indent(summary))
    if chat.payload.get("proceed_from_toggle_reminder"):
        return msg.events.edit.toggle_reminder_succeeded(chat.payload)
    return msg.events.edit.edit_event_cycle_succeeded(chat.payload)


def create_edit_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=edit_event", shorten_uuid(user_id))
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
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing edit event chat: step=%s, text=%r", chat.current_step, text)
    handlers = {
        EditEventSteps.ENTER_NAME.value: _process_event_name,
        EditEventSteps.SELECT_OPTION.value: _process_selected_edit_option,
        EditEventSteps.ENTER_NEW_NAME.value: _process_new_event_name,
        EditEventSteps.TOGGLE_REMINDER.value: _process_toggle_reminder,
        EditEventSteps.ENTER_NEW_EVENT_CYCLE.value: _process_new_event_cycle,
    }
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_edit_event_chat: {chat.current_step}")
