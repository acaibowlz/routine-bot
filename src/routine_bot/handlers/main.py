import logging

import psycopg
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexMessage,
    MessagingApi,
    ReplyMessageRequest,
    TemplateMessage,
    TextMessage,
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
    UnfollowEvent,
)

import routine_bot.db.chats as chat_db
import routine_bot.db.events as event_db
import routine_bot.db.users as user_db
import routine_bot.messages as msg
from routine_bot.constants import DATABASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from routine_bot.enums.chat import ChatStatus, ChatType
from routine_bot.enums.command import SUPPORTED_COMMANDS, Command
from routine_bot.enums.steps import DoneEventSteps, NewEventSteps, UserSettingsSteps
from routine_bot.errors import ChatNotFoundError, InvalidChatTypeError, InvalidCommandError
from routine_bot.handlers.events import (
    create_delete_event_chat,
    create_done_event_chat,
    create_edit_event_chat,
    create_find_event_chat,
    create_new_event_chat,
    create_receive_event_chat,
    create_revoke_event_chat,
    create_share_event_chat,
    handle_delete_event_chat,
    handle_done_event_chat,
    handle_edit_event_chat,
    handle_find_event_chat,
    handle_new_event_chat,
    handle_receive_event_chat,
    handle_revoke_event_chat,
    handle_share_event_chat,
    handle_view_all_chat,
    process_selected_done_date,
    process_selected_start_date,
)
from routine_bot.handlers.users import (
    create_user_settings_chat,
    handle_user_settings_chat,
    process_new_time_slot_selection,
)
from routine_bot.models import ChatData
from routine_bot.utils import format_logger_name, sanitize_msg

logger = logging.getLogger(format_logger_name(__name__))

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


def _handle_command(text: str, user_id: str, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    command_handlers = {
        Command.NEW.value: create_new_event_chat,
        Command.FIND.value: create_find_event_chat,
        Command.DELETE.value: create_delete_event_chat,
        Command.VIEW_ALL.value: handle_view_all_chat,
        Command.DONE.value: create_done_event_chat,
        Command.EDIT.value: create_edit_event_chat,
        Command.SHARE.value: create_share_event_chat,
        Command.RECEIVE.value: create_receive_event_chat,
        Command.REVOKE.value: create_revoke_event_chat,
        Command.SETTINGS.value: create_user_settings_chat,
        Command.MENU.value: lambda user_id, conn: msg.users.menu.format_menu(),
        Command.HELP.value: lambda user_id, conn: msg.users.help.format_help(),
    }

    handler = command_handlers.get(text)
    if handler:
        return handler(user_id, conn)
    raise InvalidCommandError(f"Invalid command in _handle_command: {text}")


def _handle_ongoing_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage | FlexMessage:
    ongoing_chat_handlers = {
        ChatType.NEW_EVENT.value: handle_new_event_chat,
        ChatType.FIND_EVENT.value: handle_find_event_chat,
        ChatType.DELETE_EVENT.value: handle_delete_event_chat,
        ChatType.DONE_EVENT.value: handle_done_event_chat,
        ChatType.EDIT_EVENT.value: handle_edit_event_chat,
        ChatType.SHARE_EVENT.value: handle_share_event_chat,
        ChatType.RECEIVE_EVENT.value: handle_receive_event_chat,
        ChatType.REVOKE_EVENT.value: handle_revoke_event_chat,
        ChatType.USER_SETTINGS.value: handle_user_settings_chat,
    }

    handler = ongoing_chat_handlers.get(chat.chat_type)
    if handler:
        return handler(text, chat, conn)
    raise InvalidChatTypeError(f"Invalid chat type in handle_ongoing_chat: {chat.chat_type}")


def _get_reply_message(text: str, user_id: str) -> TextMessage | TemplateMessage | FlexMessage:
    logger.debug(f"Message received: {text}")
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        ongoing_chat_id = chat_db.get_ongoing_chat_id(user_id, conn)

        if ongoing_chat_id is None:
            if text == Command.ABORT:
                return msg.abort.no_ongoing_chat()
            if not text.startswith("/"):
                return msg.users.greeting.random()
            if text not in SUPPORTED_COMMANDS:
                return msg.error.unrecognized_command()
            return _handle_command(text, user_id, conn)

        chat = chat_db.get_chat(ongoing_chat_id, conn)
        if chat is None:
            raise ChatNotFoundError(f"Chat not found: {ongoing_chat_id}")
        logger.debug(f"Ongoing chat found: {chat.chat_id}")
        logger.debug(f"Chat type: {chat.chat_type}")
        logger.debug(f"Current step: {chat.current_step}")

        if text == Command.ABORT:
            logger.info(f"Aborting chat: {chat.chat_id}")
            chat_db.update_chat_status(chat, ChatStatus.ABORTED.value, conn, logger)
            return msg.abort.ongoing_chat_aborted()

        return _handle_ongoing_chat(text, chat, conn)


# --------------------------- LINE Event Handlers ---------------------------- #


@handler.add(FollowEvent)
def handle_user_added(follow_event: FollowEvent) -> None:
    if follow_event.source is None:
        raise AttributeError("Source not found in the event object")
    if follow_event.source.user_id is None:
        raise AttributeError("User ID no found in the event source object")
    user_id = follow_event.source.user_id

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
            ReplyMessageRequest(
                reply_token=follow_event.reply_token,
                messages=[msg.users.welcome.format_welcome()],
            )
        )


@handler.add(UnfollowEvent)
def handle_user_blocked(unfollow_event: UnfollowEvent) -> None:
    if not unfollow_event.source:
        raise AttributeError("Source not found in the event object")
    if not unfollow_event.source.user_id:
        raise AttributeError("User ID no found in the event source")
    user_id = unfollow_event.source.user_id
    logger.info(f"Blocked by: {user_id}")

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        if not user_db.user_exists(user_id, conn):
            logger.warning("User is not found in the database")
        else:
            user_db.set_user_activeness(user_id, False, conn)
            event_db.set_all_events_activeness_by_user(user_id, False, conn)


@handler.add(PostbackEvent)
def handle_postback(postback_event: PostbackEvent) -> None:
    logger.debug(f"Postback data: {postback_event.postback.data}")
    logger.debug(f"Postback params: {postback_event.postback.params}")

    chat_id = postback_event.postback.data
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        chat = chat_db.get_chat(chat_id, conn)
        if chat is None:
            raise ChatNotFoundError(f"Chat not found: {chat_id}")

        postback_handlers = {
            (ChatType.NEW_EVENT, NewEventSteps.SELECT_START_DATE): process_selected_start_date,
            (ChatType.USER_SETTINGS, UserSettingsSteps.SELECT_NEW_TIME_SLOT): process_new_time_slot_selection,
            (ChatType.DONE_EVENT, DoneEventSteps.SELECT_DONE_DATE): process_selected_done_date,
        }
        handler = postback_handlers.get((chat.chat_type, chat.current_step))
        if not handler:
            return None
        reply_msg = handler(postback_event, chat, conn)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=postback_event.reply_token, messages=[reply_msg]))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(msg_event: MessageEvent) -> None:
    if not msg_event.source:
        raise AttributeError("Source not found in the event object")
    if not msg_event.source.user_id:
        raise AttributeError("User ID no found in the event source")
    user_id = msg_event.source.user_id

    text = sanitize_msg(msg_event.message.text)
    reply_msg = _get_reply_message(text=text, user_id=user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=msg_event.reply_token, messages=[reply_msg]))
