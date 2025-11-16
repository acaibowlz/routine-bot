import logging
import uuid

import psycopg
from linebot.v3.messaging import TemplateMessage, TextMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.records as record_db
import routine_bot.db.shares as share_db
import routine_bot.db.users as user_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.options import ConfirmDeletionOptions
from routine_bot.enums.steps import DeleteEventSteps
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name_entry(text: str, chat: ChatData, conn: psycopg.Connection) -> TextMessage | TemplateMessage:
    logger.info("Process delete event name input")
    event_name = text

    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name input: {event_name}, error msg={error_msg}")
        return TextMessage(text=error_msg)
    event_id = event_db.get_event_id(chat.user_id, event_name, conn)
    if event_id is None:
        logger.info(f"Event name not found: {event_name}")
        return msg.info.event_name_not_found(event_name)

    event = event_db.get_event(event_id, conn)
    assert event is not None, "Event is not suppose to be missing"
    chat.payload["event_id"] = event_id
    chat.current_step = DeleteEventSteps.CONFIRM_DELETION.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Adding to payload: event_id={event_id}")
    logger.info(f"Setting current_step={chat.current_step}")
    return msg.events.delete.comfirm_event_deletion(event)


def _process_confirm_deletion(text: str, chat: ChatData, conn: psycopg.Connection) -> TextMessage | TemplateMessage:
    logger.info("Processing delete event confirm deletion")
    event_id = chat.payload["event_id"]
    event = event_db.get_event(event_id, conn)
    if event is None:
        raise ValueError(f"Event not found: {event_id}")

    if text == ConfirmDeletionOptions.DELETE:
        share_db.delete_shares_by_event_id(event_id, conn)
        record_db.delete_records_by_event_id(event_id, conn)
        event_db.delete_event(event_id, conn)
        user_db.increment_user_event_count(event.user_id, -1, conn)
        logger.info("┌── Deleting Event ─────────────────────────")
        logger.info(f"│ ID: {event.event_id}")
        logger.info(f"│ User: {event.user_id}")
        logger.info(f"│ Name: {event.event_name}")
        logger.info("└───────────────────────────────────────────")

        chat.current_step = None
        chat.status = ChatStatus.COMPLETED.value
        chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
        chat_db.set_chat_status(chat.chat_id, chat.status, conn)
        logger.info(f"Setting current_step={chat.current_step}")
        logger.info(f"Finishing chat: {chat.chat_id}")
        return msg.events.delete.succeeded(event.event_name)
    elif text == ConfirmDeletionOptions.CANCEL:
        chat.current_step = None
        chat.status = ChatStatus.COMPLETED.value
        chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
        chat_db.set_chat_status(chat.chat_id, chat.status, conn)
        logger.info("Cancelling deletion")
        logger.info(f"Setting current_step={chat.current_step}")
        logger.info(f"Finishing chat: {chat.chat_id}")
        return msg.events.delete.cancelled()
    else:
        logger.info(f"Invalid delete confirmation entry: {text}")
        return msg.events.delete.invalid_delete_confirmation(event)


def create_delete_event_chat(user_id: str, conn: psycopg.Connection) -> TextMessage:
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


def handle_delete_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TextMessage | TemplateMessage:
    if chat.current_step == DeleteEventSteps.ENTER_NAME:
        return _process_event_name_entry(text, chat, conn)
    elif chat.current_step == DeleteEventSteps.CONFIRM_DELETION:
        return _process_confirm_deletion(text, chat, conn)
    else:
        raise AssertionError(f"Unknown step in handle_delete_event_chat: {chat.current_step}")
