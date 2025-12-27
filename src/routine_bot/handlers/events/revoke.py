import logging
import uuid

import psycopg
from linebot.v3.messaging import FlexMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.shares as share_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import RevokeEventSteps
from routine_bot.errors import InvalidStepError
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, get_user_profile, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection):
    logger.info("Processing event name")
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

    recipient_ids = share_db.list_recipients_by_event(event.event_id, conn)
    if not recipient_ids:
        pass
    recipient_info = []
    for recipient_id in recipient_ids:
        profile = get_user_profile(recipient_id)
        recipient_info.append((recipient_id, profile.display_name))


def create_revoke_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: revoke event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.REVOKE_EVENT.value,
        current_step=RevokeEventSteps.ENTER_NAME.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.revoke.enter_event_name()


def handle_revoke_event_chat(text: str, chat: ChatData, conn: psycopg.Connection):
    raise InvalidStepError(f"Invalid step in handle_share_event_chat: {chat.current_step}")
