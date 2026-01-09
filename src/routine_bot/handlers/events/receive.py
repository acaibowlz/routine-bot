import base64
import binascii
import logging
import uuid

import psycopg
from linebot.v3.messaging import FlexMessage

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.shares as share_db
import routine_bot.messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import ReceiveEventSteps
from routine_bot.errors import EventNotFoundError, InvalidStepError
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData, ShareData
from routine_bot.utils import get_user_profile

logger = logging.getLogger(format_logger_name(__name__))


def _extract_event_id(share_code: str) -> str:
    padded = share_code + "=" * (-len(share_code) % 4)
    return base64.urlsafe_b64decode(padded.encode()).decode()


def _process_share_code(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing share code")
    share_code = text

    try:
        event_id = _extract_event_id(share_code)
    except (AttributeError, binascii.Error, UnicodeDecodeError):
        cxt_logger.debug("Failed to decode share code: %r", share_code)
        return msg.events.receive.invalid_share_code()

    event = event_db.get_event_by_id(event_id, conn)
    if event is None:
        raise EventNotFoundError(f"Event not found: {event_id}")
    if event.event_cycle is None:
        raise AttributeError(f"Event does not have a valid event cycle: {event.event_id}")
    if event.next_due_at is None:
        raise AttributeError(f"Event does not have a valid next due date: {event.event_id}")

    recipient_id = chat.user_id
    chat.payload = chat_db.patch_chat_payload(
        chat=chat, new_data={"event_name": event.event_name}, conn=conn, logger=logger
    )

    if share_db.is_share_duplicated(event_id, recipient_id, conn):
        cxt_logger.debug("Share ignored: duplicated (recipient=%s, event_id=%s)", recipient_id, event_id)
        chat_db.finalize_chat(chat, conn, logger)
        return msg.events.receive.duplicated(chat.payload)

    share_id = str(uuid.uuid4())
    share = ShareData(
        share_id=share_id,
        event_id=event_id,
        event_name=event.event_name,
        owner_id=event.user_id,
        recipient_id=recipient_id,
    )
    share_db.add_share(share, conn)
    event_db.increment_event_share_count(event_id, 1, conn)

    owner_profile = get_user_profile(share.owner_id)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={
            "owner_name": owner_profile.display_name,
            "next_due_at": event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime("%Y-%m-%d"),
            "event_cycle": event.event_cycle,
        },
        conn=conn,
        logger=logger,
    )
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── Share Received ────────────────────────",
            f"│ Share ID: {share_id}",
            f"│ Event Name: {event.event_name}",
            f"│ Event ID: {event_id}",
            f"│ Owner: {share.owner_id}",
            f"│ Recipient: {share.recipient_id}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("Share received successfully\n%s", indent(summary))

    return msg.events.receive.succeeded(chat.payload)


def create_receive_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=receive_event", shorten_uuid(user_id))

    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.RECEIVE_EVENT.value,
        current_step=ReceiveEventSteps.ENTER_CODE.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.events.receive.enter_share_code()


def handle_receive_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing receive event chat: step=%s, text=%r", chat.current_step, text)
    handlers = {ReceiveEventSteps.ENTER_CODE.value: _process_share_code}
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_receive_event_chat: {chat.current_step}")
