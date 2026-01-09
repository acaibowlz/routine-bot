import base64
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
from routine_bot.logger import add_context, format_logger_name, shorten_uuid
from routine_bot.models import ChatData
from routine_bot.utils import validate_event_name

logger = logging.getLogger(format_logger_name(__name__))


def _create_share_code(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).rstrip(b"=").decode()


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
        cxt_logger.debug("Event not found: user_id=%s, event_name=%r", shorten_uuid(user_id), event_name)
        return msg.error.event_name_not_found(event_name)

    chat.payload = chat_db.patch_chat_payload(chat=chat, new_data={"event_name": event_name}, conn=conn, logger=logger)

    if not event.reminder_enabled:
        cxt_logger.info("Share rejected: reminder disabled (event_id=%s)", shorten_uuid(event.event_id))
        chat_db.finalize_chat(chat, conn, logger)
        return msg.events.share.invalid_event_must_enable_reminder(chat.payload)

    if event.share_count >= 4:
        cxt_logger.info("Share rejected: max share count reached)")
        chat_db.finalize_chat(chat, conn, logger)
        return msg.events.share.reached_max_share_count(chat.payload)

    chat.payload = chat_db.patch_chat_payload(
        chat=chat, new_data={"share_code": _create_share_code(event.event_id)}, conn=conn, logger=logger
    )
    chat_db.finalize_chat(chat, conn, logger)

    cxt_logger.info(
        "Share event initialized: user=%s, event=%r (%s)",
        shorten_uuid(user_id),
        event.event_name,
        shorten_uuid(event.event_id),
    )
    return msg.events.share.show_recipient_instruction(chat.payload)


def create_share_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=share_event", shorten_uuid(user_id))

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
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing share event chat: step=%s, text=%r", chat.current_step, text)

    handlers = {ShareEventSteps.ENTER_NAME.value: _process_event_name}
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_share_event_chat: {chat.current_step}")
