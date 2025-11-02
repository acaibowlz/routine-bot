import logging
import uuid
from datetime import datetime

import psycopg
from linebot.v3.messaging import (
    Message,
    TemplateMessage,
)
from linebot.v3.webhooks import PostbackEvent

import routine_bot.db.chats as chat_db
import routine_bot.db.users as user_db
import routine_bot.messages as msg
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.steps import UserSettingsSteps
from routine_bot.enums.user_settings import UserSettingsOptions
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def _prepare_new_notification_selection(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Option selected: new notification slot")
    option = UserSettingsOptions.NOTIFICATION_SLOT.value
    user = user_db.get_user(chat.user_id, conn)
    if user is None:
        raise ValueError(f"User not found: {chat.user_id}")
    chat.payload["option"] = option
    chat.payload["chat_id"] = chat.chat_id
    chat.payload["current_slot"] = user.notification_slot.strftime("%H:%M")
    chat.current_step = UserSettingsSteps.SELECT_NEW_NOTIFICATION_SLOT.value
    chat_db.set_chat_payload(chat.chat_id, chat.payload, conn)
    chat_db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Adding to payload: option={option}")
    logger.info(f"Adding to payload: chat_id={chat.chat_id}")
    logger.info(f"Adding to payload: current_slot={chat.payload['current_slot']}")
    logger.info(f"Setting current_step={chat.current_step}")
    return msg.user_settings.select_new_notification_slot(chat.payload)


def process_user_settings_new_notification_slot_selection(
    postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection
):
    logger.info("Processing new notification slot selection")
    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")
    time_slot = postback.postback.params["time"]
    if time_slot.split(":")[1] != "00":
        logger.debug(f"Not a time slot: {time_slot}")
        return msg.user_settings.invalid_notification_slot(chat.payload)
    else:
        time_slot = datetime.strptime(time_slot, "%H:%M").time()
        logger.info(f"New notification slot: {time_slot}")
        user_db.set_user_notification_slot(chat.user_id, time_slot, conn)
        chat_db.set_chat_current_step(chat.chat_id, None, conn)
        chat_db.set_chat_status(chat.chat_id, ChatStatus.COMPLETED.value, conn)
        logger.info(f"Setting current_step={chat.current_step}")
        logger.info(f"Finishing chat: {chat.chat_id}")
        return msg.user_settings.notification_slot_updated(chat.payload)


def create_user_settings_chat(user_id: str, conn: psycopg.Connection) -> TemplateMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: user settings")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=ChatType.USER_SETTINGS.value,
        current_step=UserSettingsSteps.SELECT_OPTION.value,
        payload={},
        status=ChatStatus.ONGOING.value,
    )
    chat_db.add_chat(chat, conn)
    return msg.user_settings.select_option()


def handle_user_settings_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == UserSettingsSteps.SELECT_OPTION:
        logger.info("Processing user settings option input")
        if text == "更改提醒時段":
            return _prepare_new_notification_selection(chat, conn)
        else:
            logger.info(f"Invalid user settings option input: {text}")
            return msg.user_settings.invalid_input_for_option()
    elif chat.current_step == UserSettingsSteps.SELECT_NEW_NOTIFICATION_SLOT:
        logger.info("Text input is not expected at current step")
        return msg.user_settings.invalid_input_for_notification_slot(chat.payload)
    else:
        logger.error(f"Unexpected step in handle_user_settings_chat: {chat.current_step}")
        return msg.error.unexpected_error()
