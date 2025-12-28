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
from routine_bot.errors import EventNotFoundError, InvalidStepError
from routine_bot.models import ChatData, EventData
from routine_bot.utils import format_logger_name, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Process event name")
    event_name = text
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name. Input: {event_name}, Error msg: {''.join(error_msg)}")
        return msg.error.error(error_msg)
    user_id = chat.user_id
    event = event_db.get_event_by_name(user_id, event_name, conn)
    if event is None:
        logger.info(f"Event not found. User ID: {user_id}, Event Name: {event_name}")
        return msg.error.event_name_not_found(event_name)

    chat_db.update_chat_current_step(chat, DeleteEventSteps.CONFIRM_DELETION.value, conn, logger)
    payload_new_data = {
        "event_id": event.event_id,
        "event_name": event.event_name,
        "last_done_at": event.last_done_at.astimezone(TZ_TAIPEI).strftime("%Y-%m-%d"),
    }
    if event.reminder_enabled and event.next_due_at:
        payload_new_data["reminder_enabled"] = "True"
        payload_new_data["next_due_at"] = event.next_due_at.astimezone(TZ_TAIPEI).strftime("%Y-%m-%d")
    chat.payload = chat_db.update_chat_payload(chat=chat, new_data=payload_new_data, conn=conn, logger=logger)
    return msg.events.delete.comfirm_event_deletion(chat.payload)


def _confirm_deletion(event: EventData, chat: ChatData, conn: psycopg.Connection):
    logger.info("┌── Deleting Event ─────────────────────────")
    logger.info(f"│ Event Name: {event.event_name}")
    logger.info(f"│ Event ID: {event.event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info("└───────────────────────────────────────────")
    share_db.delete_shares_by_event_id(event.event_id, conn)
    record_db.delete_records_by_event_id(event.event_id, conn)
    event_db.delete_event(event.event_id, conn)
    user_db.increment_user_event_count(event.user_id, -1, conn)
    chat_db.finalize_chat(chat, conn, logger)
    return msg.events.delete.succeeded(chat.payload)


def _cancel_deletion(event: EventData, chat: ChatData, conn: psycopg.Connection):
    logger.info("Cancelling deletion")
    chat_db.finalize_chat(chat, conn, logger)
    return msg.events.delete.cancelled(chat.payload)


def _process_confirm_deletion(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing delete event confirm deletion")
    event_id = chat.payload["event_id"]
    event = event_db.get_event_by_id(event_id, conn)
    if event is None:
        raise EventNotFoundError(f"Event not found: {event_id}")

    handlers = {
        ConfirmDeletionOptions.CANCEL.value: _cancel_deletion,
        ConfirmDeletionOptions.DELETE.value: _confirm_deletion,
    }
    handler = handlers.get(text, lambda event, chat, conn: msg.events.delete.invalid_delete_confirmation(chat.payload))
    return handler(event, chat, conn)


def create_delete_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: delete event")
    logger.info(f"Chat ID: {chat_id}")
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
    handlers = {
        DeleteEventSteps.ENTER_NAME.value: _process_event_name,
        DeleteEventSteps.CONFIRM_DELETION.value: _process_confirm_deletion,
    }
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    else:
        raise InvalidStepError(f"Invalid step in handle_delete_event_chat: {chat.current_step}")
