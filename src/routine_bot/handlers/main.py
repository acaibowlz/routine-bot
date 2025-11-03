import logging

import psycopg
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    Message,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import FollowEvent, MessageEvent, PostbackEvent, TextMessageContent, UnfollowEvent

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.users as user_db
import routine_bot.messages as msg
from routine_bot.constants import DATABASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.command import SUPPORTED_COMMANDS, Command
from routine_bot.enums.steps import NewEventSteps, UserSettingsSteps
from routine_bot.handlers.events import (
    create_delete_event_chat,
    create_find_event_chat,
    create_new_event_chat,
    create_view_all_chat,
    handle_delete_event_chat,
    handle_find_event_chat,
    handle_new_event_chat,
    process_new_event_start_date_selection,
)
from routine_bot.handlers.user import (
    create_menu_chat,
    create_user_settings_chat,
    handle_user_settings_chat,
    process_user_settings_new_notification_slot_selection,
)
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, sanitize_msg

logger = logging.getLogger(format_logger_name(__name__))

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


def _handle_command(cmd: str, user_id: str, conn: psycopg.Connection) -> Message:
    if cmd == Command.NEW:
        return create_new_event_chat(user_id, conn)
    elif cmd == Command.FIND:
        return create_find_event_chat(user_id, conn)
    elif cmd == Command.DELETE:
        return create_delete_event_chat(user_id, conn)
    elif cmd == Command.VIEW_ALL:
        return create_view_all_chat(user_id, conn)
    elif cmd == Command.SETTINGS:
        return create_user_settings_chat(user_id, conn)
    elif cmd == Command.MENU:
        return create_menu_chat(user_id, conn)
    else:
        raise AssertionError(f"Unknown command in _handle_command: {cmd}")


def _handle_ongoing_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.chat_type == ChatType.NEW_EVENT:
        return handle_new_event_chat(text, chat, conn)
    elif chat.chat_type == ChatType.FIND_EVENT:
        return handle_find_event_chat(text, chat, conn)
    elif chat.chat_type == ChatType.DELETE_EVENT:
        return handle_delete_event_chat(text, chat, conn)
    elif chat.chat_type == ChatType.USER_SETTINGS:
        return handle_user_settings_chat(text, chat, conn)
    else:
        raise AssertionError(f"Unknown chat type in handle_ongoing_chat: {chat.chat_type}")


def _get_reply_message(text: str, user_id: str) -> Message:
    logger.debug(f"Message received: {text}")
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        ongoing_chat_id = chat_db.get_ongoing_chat_id(user_id, conn)

        if ongoing_chat_id is None:
            if text == Command.ABORT:
                return msg.info.no_ongoing_chat()
            if not text.startswith("/"):
                return msg.user.greeting.random()
            if text not in SUPPORTED_COMMANDS:
                return msg.info.unrecognized_command()
            return _handle_command(text, user_id, conn)

        chat = chat_db.get_chat(ongoing_chat_id, conn)
        assert chat is not None, "Chat is not suppose to be missing"
        logger.debug(f"Ongoing chat found: {chat.chat_id}")
        logger.debug(f"Chat type: {chat.chat_type}")
        logger.debug(f"Current step: {chat.current_step}")

        if text == Command.ABORT:
            chat.status = ChatStatus.ABORTED.value
            chat_db.set_chat_status(chat.chat_id, ChatStatus.ABORTED.value, conn)
            logger.info(f"Aborting chat: {chat.chat_id}")
            return msg.info.ongoing_chat_aborted()

        return _handle_ongoing_chat(text, chat, conn)


# --------------------------- LINE Event Handlers ---------------------------- #


@handler.add(FollowEvent)
def handle_user_added(event: FollowEvent) -> None:
    if event.source is None:
        raise AttributeError("Source not found in the event object")
    if event.source.user_id is None:
        raise AttributeError("User ID no found in the event source object")
    user_id = event.source.user_id

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        if not user_db.user_exists(user_id, conn):
            logger.info(f"Added by: {user_id}")
            user_db.add_user(user_id, conn)
        else:
            logger.info(f"Unblocked by: {user_id}")
            user_db.set_user_activeness(user_id, True, conn)
            event_db.set_all_events_activeness_by_user(user_id, True, conn)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="hello my new friend!")])
        )


@handler.add(UnfollowEvent)
def handle_user_blocked(event: UnfollowEvent) -> None:
    if not event.source:
        raise AttributeError("Source not found in the event object")
    if not event.source.user_id:
        raise AttributeError("User ID no found in the event source")
    user_id = event.source.user_id
    logger.info(f"Blocked by: {user_id}")

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        if not user_db.user_exists(user_id, conn):
            logger.warning("User not found in database")
        else:
            user_db.set_user_activeness(user_id, False, conn)
            event_db.set_all_events_activeness_by_user(user_id, False, conn)


@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent) -> None:
    logger.debug(f"Postback data: {event.postback.data}")
    logger.debug(f"Postback params: {event.postback.params}")
    chat_id = event.postback.data
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        chat = chat_db.get_chat(chat_id, conn)
        if chat is None:
            raise ValueError(f"Chat not found: {chat_id}")
        # only proceed if status and current step matches
        if chat.chat_type == ChatType.NEW_EVENT and chat.current_step == NewEventSteps.SELECT_START_DATE:
            reply_msg = process_new_event_start_date_selection(event, chat, conn)
        elif (
            chat.chat_type == ChatType.USER_SETTINGS
            and chat.current_step == UserSettingsSteps.SELECT_NEW_NOTIFICATION_SLOT
        ):
            reply_msg = process_user_settings_new_notification_slot_selection(event, chat, conn)
        else:
            return None

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_msg]))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    if not event.source:
        raise AttributeError("Source not found in the event object")
    if not event.source.user_id:
        raise AttributeError("User ID no found in the event source")
    user_id = event.source.user_id

    text = sanitize_msg(event.message.text)
    reply_msg = _get_reply_message(text=text, user_id=user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_msg]))
