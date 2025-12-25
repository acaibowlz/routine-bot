import logging
import uuid

import psycopg
from linebot.v3.messaging import FlexMessage, TemplateMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import ShareEventSteps
from routine_bot.errors import InvalidStepError
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name_entry(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing event name entry")
    event_name = text

    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name entry: {event_name}, error msg={error_msg}")
        return msg.error.error([error_msg])
    user_id = chat.user_id
    event = event_db.get_event_by_name(user_id, event_name, conn)
    if event is None:
        logger.info(f"Event not found: {event_name}")
        return msg.error.event_name_not_found(event_name)
    chat.payload = chat_db.update_chat_payload(chat=chat, new_data={"event_name": event_name}, conn=conn, logger=logger)

    if not event.reminder_enabled:
        logger.info("Failed to share event: Event did not enable reminder")
        chat_db.finish_chat(chat, conn, logger)
        return msg.events.share.invalid_event_must_enable_reminder(chat.payload)

    if event.share_count >= 4:
        logger.info("Failed to share event: Event has reached max share count")
        chat_db.finish_chat(chat, conn, logger)
        return msg.events.share.reached_max_share_count(chat.payload)

    chat_db.finish_chat(chat, conn, logger)
    chat.payload = chat_db.update_chat_payload(
        chat=chat, new_data={"event_id": event.event_id}, conn=conn, logger=logger
    )
    return msg.events.share.show_recipient_instruction(chat.payload)


def create_share_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: share event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.SHARE_EVENT.value,
        current_step=ShareEventSteps.ENTER_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.share.enter_event_name()


def handle_share_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    if chat.current_step == ShareEventSteps.ENTER_NAME:
        return _process_event_name_entry(text, chat, conn)
    else:
        raise InvalidStepError(f"invalid step in handle_share_event_chat: {chat.current_step}")
