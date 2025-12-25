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
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def _process_selected_option(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Processing user settings option input")
    if text == UserSettingsOptions.TIME_SLOT:
        return _prepare_new_time_slot_selection(chat, conn)
    else:
        logger.info(f"Invalid user settings option: {text}")
        return msg.users.settings.invalid_input_for_option(chat.payload)


def _prepare_new_time_slot_selection(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Option selected: new time slot")
    user = user_db.get_user(chat.user_id, conn)
    if user is None:
        raise UserNotFoundError(f"User not found: {chat.user_id}")
    chat_db.update_chat_current_step(chat, UserSettingsSteps.SELECT_NEW_TIME_SLOT.value, conn, logger)
    chat.payload = chat_db.update_chat_payload(
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
    logger.info("Processing new time slot selection")
    if postback.postback.params is None:
        raise AttributeError("Postback contains no data")
    time_slot = postback.postback.params["time"]
    if time_slot.split(":")[1] != "00":
        logger.info(f"Not a time slot: {time_slot}")
        return msg.users.settings.invalid_time_slot(chat.payload)
    else:
        time_slot = datetime.strptime(time_slot, "%H:%M").time()
        logger.info(f"New notification slot: {time_slot}")
        user_db.set_user_time_slot(chat.user_id, time_slot, conn)
        chat_db.finish_chat(chat, conn, logger)
        chat.payload = chat_db.update_chat_payload(
            chat=chat, new_data={"new_slot": time_slot.strftime("%H:%M")}, conn=conn, logger=logger
        )
        return msg.users.settings.succeeded(chat.payload)


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
    return msg.users.settings.select_option()


def handle_user_settings_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    if chat.current_step == UserSettingsSteps.SELECT_OPTION:
        return _process_selected_option(text, chat, conn)
    elif chat.current_step == UserSettingsSteps.SELECT_NEW_TIME_SLOT:
        return msg.users.settings.invalid_input_for_time_slot(chat.payload)
    else:
        raise InvalidStepError(f"Invalid step in handle_user_settings_chat: {chat.current_step}")
