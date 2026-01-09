import logging
import uuid

import psycopg
from linebot.v3.messaging import FlexMessage, TemplateMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.records as record_db
import routine_bot.db.shares as share_db
import routine_bot.db.users as user_db
import routine_bot.messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.options import ConfirmDeletionOptions
from routine_bot.enums.steps import DeleteEventSteps
from routine_bot.errors import InvalidStepError
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData
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
    event = event_db.get_event_by_name(user_id, event_name, conn)
    if event is None:
        cxt_logger.debug("Event not found: user_id=%s, event_name=%r", user_id, event_name)
        return msg.error.event_name_not_found(event_name)

    cxt_logger.info("Event selected for deletion: %r (%s)", event.event_name, shorten_uuid(event.event_id))
    chat_db.set_chat_current_step(chat.chat_id, DeleteEventSteps.CONFIRM_DELETION.value, conn)

    payload_new_data = {
        "event_id": event.event_id,
        "event_name": event.event_name,
        "last_done_at": event.last_done_at.astimezone(TZ_TAIPEI).strftime("%Y-%m-%d"),
    }
    if event.reminder_enabled and event.next_due_at:
        payload_new_data["reminder_enabled"] = "True"
        payload_new_data["next_due_at"] = event.next_due_at.astimezone(TZ_TAIPEI).strftime("%Y-%m-%d")
    else:
        payload_new_data["reminder_enabled"] = "False"

    chat.payload = chat_db.patch_chat_payload(chat=chat, new_data=payload_new_data, conn=conn, logger=logger)
    return msg.events.delete.comfirm_event_deletion(chat.payload)


def _confirm_deletion(chat: ChatData, conn: psycopg.Connection):
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.info("Deletion confirmed")

    event_id = chat.payload["event_id"]
    event = event_db.get_event_by_id(event_id, conn)
    share_db.delete_shares_by_event(event.event_id, conn)
    record_db.delete_records_by_event(event.event_id, conn)
    event_db.delete_event(event.event_id, conn)
    user_db.increment_user_event_count(event.user_id, -1, conn)
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── Event Deleted ─────────────────────────",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event.event_id}",
            f"│ User: {chat.user_id}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Event deleted successfully\n%s", indent(summary))
    return msg.events.delete.succeeded(chat.payload)


def _cancel_deletion(chat: ChatData, conn: psycopg.Connection):
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.info("Deletion cancelled")
    chat_db.finalize_chat(chat, conn, logger)
    return msg.events.delete.cancelled(chat.payload)


def _process_confirm_deletion(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing confirm deletion")
    handlers = {
        ConfirmDeletionOptions.CANCEL.value: _cancel_deletion,
        ConfirmDeletionOptions.DELETE.value: _confirm_deletion,
    }
    handler = handlers.get(text)
    if handler:
        return handler(chat, conn)
    cxt_logger.debug("Invalid entry: %r", text)
    return msg.events.delete.invalid_delete_confirmation(chat.payload)


def create_delete_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=delete_event", shorten_uuid(user_id))
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.DELETE_EVENT.value,
        current_step=DeleteEventSteps.ENTER_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.delete.enter_event_name()


def handle_delete_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing delete event chat: step=%s, text=%r", chat.current_step, text)
    handlers = {
        DeleteEventSteps.ENTER_NAME.value: _process_event_name,
        DeleteEventSteps.CONFIRM_DELETION.value: _process_confirm_deletion,
    }
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    else:
        raise InvalidStepError(f"Invalid step in handle_delete_event_chat: {chat.current_step}")
