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
from routine_bot.errors import InvalidStepError
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData
from routine_bot.utils import get_user_profile, validate_event_name

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
        cxt_logger.debug("Event not found: user=%s, event_name=%r", user_id, event_name)
        return msg.error.event_name_not_found(event_name)

    recipient_ids = share_db.list_recipients_by_event(event.event_id, conn)

    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"event_name": event.event_name},
        conn=conn,
        logger=logger,
    )

    if not recipient_ids:
        cxt_logger.debug("No recipients to revoke: event_id=%s", event.event_id)
        chat_db.finalize_chat(chat, conn, logger)
        return msg.events.revoke.no_recipient(chat.payload)

    recipient_info = {}
    for recipient_id in recipient_ids:
        profile = get_user_profile(recipient_id)
        recipient_info[profile.display_name] = recipient_id

    cxt_logger.info(
        "%d recipients found for event revocation: %r (%s)",
        len(recipient_info),
        event.event_name,
        shorten_uuid(event.event_id),
    )

    chat_db.set_chat_current_step(chat.chat_id, RevokeEventSteps.SELECT_RECIPIENT.value, conn)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"recipient_info": str(recipient_info), "event_id": event.event_id},
        conn=conn,
        logger=logger,
    )
    return msg.events.revoke.select_recipient(chat.payload)


def _process_selected_recipient(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing selected recipient")
    selected_recipient = text

    recipient_info = ast.literal_eval(chat.payload["recipient_info"])
    if selected_recipient not in recipient_info:
        cxt_logger.debug("Invalid recipient selection: %r", selected_recipient)
        return msg.events.revoke.recipient_not_found(chat.payload)

    event_id = chat.payload["event_id"]
    recipient_id = recipient_info[selected_recipient]

    share = share_db.get_share_by_event(event_id, recipient_id, conn)
    share_db.delete_share(event_id, recipient_id, conn)

    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"selected_recipient": selected_recipient},
        conn=conn,
        logger=logger,
    )
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── Share Revoked ─────────────────────────",
            f"│ Share ID: {share.share_id}",
            f"│ Event Name: {share.event_name}",
            f"│ Event ID: {event_id}",
            f"│ Owner: {share.owner_id}",
            f"│ Recipient: {selected_recipient}",
            f"│ Recipient ID: {share.recipient_id}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Share revoked successfully\n%s", indent(summary))
    return msg.events.revoke.recipient_revoked(chat.payload)


def create_revoke_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=revoke_event", user_id)

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
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing revoke event chat: step=%s, text=%r", chat.current_step, text)
    handlers = {
        RevokeEventSteps.ENTER_NAME.value: _process_event_name,
        RevokeEventSteps.SELECT_RECIPIENT.value: _process_selected_recipient,
    }
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_revoke_event_chat: {chat.current_step}")
