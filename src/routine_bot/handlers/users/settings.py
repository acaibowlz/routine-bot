import logging
import uuid
from datetime import datetime

import psycopg
from linebot.v3.messaging import TemplateMessage
from linebot.v3.messaging.models.flex_message import FlexMessage
from linebot.v3.webhooks import PostbackEvent

import routine_bot.db.chats as chat_db
import routine_bot.db.users as user_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.options import UserSettingsOptions
from routine_bot.enums.steps import UserSettingsSteps
from routine_bot.errors import InvalidStepError, UserNotFoundError
from routine_bot.logger import add_context, format_logger_name, indent, shorten_uuid
from routine_bot.models import ChatData

logger = logging.getLogger(format_logger_name(__name__))


def _prepare_new_time_slot_selection(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.info("Option selected: New time slot")
    user = user_db.get_user(chat.user_id, conn)
    chat_db.set_chat_current_step(chat.chat_id, UserSettingsSteps.SELECT_NEW_TIME_SLOT.value, conn)
    chat.payload = chat_db.patch_chat_payload(
        chat=chat,
        new_data={"chat_id": chat.chat_id, "current_slot": user.notification_slot.strftime("%H:%M")},
        conn=conn,
        logger=logger,
    )
    return msg.users.settings.select_new_time_slot(chat.payload)


# this function is called by handle_postback in handlers/main.py
def process_new_time_slot_selection(
    postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection
) -> TemplateMessage | FlexMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing new time slot selection")

    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")

    time_slot = postback.postback.params["time"]
    if time_slot.split(":")[1] != "00":
        cxt_logger.debug("Invalid time slot selected (minute must be 00): %r", time_slot)
        return msg.users.settings.invalid_time_slot(chat.payload)
    user_db.set_user_time_slot(chat.user_id, datetime.strptime(time_slot, "%H:%M").time(), conn)
    cxt_logger.info("Time slot set to: %s", time_slot)
    chat.payload = chat_db.patch_chat_payload(chat=chat, new_data={"new_slot": time_slot}, conn=conn, logger=logger)
    chat_db.finalize_chat(chat, conn, logger)

    summary = "\n".join(
        [
            "┌── User Settings Updated ─────────────────",
            f"│ User: {shorten_uuid(chat.user_id)}",
            "│ Change: Notification time slot",
            f"│ Details: {chat.payload['current_slot']} → {chat.payload['new_slot']}",
            "└───────────────────────────────────────────",
        ]
    )
    cxt_logger.info("User settings updated successfully\n%s", indent(summary))
    return msg.users.settings.succeeded(chat.payload)


def _process_selected_option(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Processing user settings option")
    handlers = {UserSettingsOptions.TIME_SLOT.value: _prepare_new_time_slot_selection}
    handler = handlers.get(text)
    if handler:
        cxt_logger.debug("Option selected: %r", text)
        return handler(chat, conn)
    cxt_logger.debug("Invalid option: %r", text)
    return msg.users.settings.invalid_option(chat.payload)


def create_user_settings_chat(user_id: str, conn: psycopg.Connection) -> TemplateMessage:
    chat_id = str(uuid.uuid4())
    cxt_logger = add_context(logger, chat_id=chat_id)
    cxt_logger.info("New chat created: user=%s, chat_type=user_settings", shorten_uuid(user_id))

    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.USER_SETTINGS.value,
        current_step=UserSettingsSteps.SELECT_OPTION.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.users.settings.select_option()


def handle_user_settings_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    cxt_logger = add_context(logger, chat_id=chat.chat_id)
    cxt_logger.debug("Routing user settings chat: step=%s, text=%r", chat.current_step, text)
    handlers = {
        UserSettingsSteps.SELECT_OPTION.value: _process_selected_option,
        UserSettingsSteps.SELECT_NEW_TIME_SLOT.value: lambda text, chat, conn: msg.users.settings.invalid_text_input(
            chat.payload
        ),
    }
    handler = handlers.get(chat.current_step)
    if handler:
        return handler(text, chat, conn)
    raise InvalidStepError(f"Invalid step in handle_user_settings_chat: {chat.current_step}")
