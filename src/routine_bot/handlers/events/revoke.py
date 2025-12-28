import ast
import logging
import uuid

import psycopg
from linebot.v3.messaging import FlexMessage, TemplateMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.shares as share_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import RevokeEventSteps
from routine_bot.errors import InvalidStepError, ShareNotFoundError
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, get_user_profile, validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_event_name(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
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
    chat.payload = chat_db.update_chat_payload(
        chat=chat,
        new_data={event_name: event.event_name},
        conn=conn,
        logger=logger,
    )
    if not recipient_ids:
        logger.info("No recipient found")
        chat_db.finalize_chat(chat, conn, logger)
        return msg.events.revoke.no_recipient(chat.payload)
    recipient_info = {}
    for recipient_id in recipient_ids:
        profile = get_user_profile(recipient_id)
        recipient_info[profile.display_name] = recipient_id
    logger.info(f"Recipient(s) found: {', '.join(recipient_info.keys())}")
    chat_db.update_chat_current_step(chat, RevokeEventSteps.SELECT_RECIPIENT.value, conn, logger)
    chat.payload = chat_db.update_chat_payload(
        chat=chat,
        new_data={"recipient_info": str(recipient_info), "event_id": event.event_id},
        conn=conn,
        logger=logger,
    )
    return msg.events.revoke.select_recipient(chat.payload)


def _process_selected_recipient(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    logger.info("Processing selected recipient")
    selected_recipient = text
    recipient_info = ast.literal_eval(chat.payload["recipient_info"])
    if selected_recipient not in recipient_info.keys():
        logger.info(f"Invalid recipient: {selected_recipient}")
        return msg.events.revoke.recipient_not_found(chat.payload)

    event_id = chat.payload["event_id"]
    recipient_id = recipient_info[selected_recipient]
    share = share_db.get_share_by_event(event_id, recipient_id, conn)
    if share is None:
        raise ShareNotFoundError(f"Share not found with event id: {event_id}, recipient id: {recipient_id}")
    logger.info("┌── Deleting Share ─────────────────────────")
    logger.info(f"│ Share ID: {share.share_id}")
    logger.info(f"│ Event Name: {share.event_name}")
    logger.info(f"│ Event ID: {event_id}")
    logger.info(f"│ Owner: {share.owner_id}")
    logger.info(f"│ Recipient: {share.recipient_id}")
    logger.info("└───────────────────────────────────────────")
    share_db.delete_share(event_id, recipient_id, conn)
    chat.payload = chat_db.update_chat_payload(
        chat=chat, new_data={"selected_recipient": selected_recipient}, conn=conn, logger=logger
    )
    chat_db.finalize_chat(chat, conn, logger)
    return msg.events.revoke.recipient_revoked(chat.payload)


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
    handlers = {
        RevokeEventSteps.ENTER_NAME.value: _process_event_name,
        RevokeEventSteps.SELECT_RECIPIENT.value: _process_selected_recipient,
    }
    handler = handlers.get(text)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_revoke_event_chat: {chat.current_step}")
