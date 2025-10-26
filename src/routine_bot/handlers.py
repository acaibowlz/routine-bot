import logging
import re
import unicodedata
import uuid
from datetime import datetime

import psycopg
import requests
from cachetools.func import ttl_cache
from dateutil.relativedelta import relativedelta
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

import routine_bot.db as db
import routine_bot.enums as enums
import routine_bot.messages as msg
from routine_bot.constants import (
    DATABASE_URL,
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    TZ_TAIPEI,
)
from routine_bot.models import ChatData, EventData, UpdateData

logger = logging.getLogger(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ------------------------------ Util Functions ------------------------------ #


@ttl_cache(maxsize=None, ttl=600)
def get_user_profile(user_id: str) -> dict[str, str]:
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}

    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch user profile: {e}")
        return {}


def sanitize_msg(msg: str) -> str:
    """
    Cleans and normalizes user input text for consistent downstream processing.

    Steps:
    1. Trim leading/trailing whitespace and newlines
    2. Normalize Unicode (NFKC) — converts fullwidth to halfwidth, etc.
    3. Collapse multiple spaces/newlines
    4. Remove invisible control characters
    """
    if not msg:
        return ""
    text = unicodedata.normalize("NFKC", msg)
    text = text.strip()
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    return text


def validate_event_name(event_name: str) -> str | None:
    """
    Return None if the event name is valid, or the error msg will be returned.
    """
    if len(event_name) < 2:
        return "事件名稱不可以少於 2 字元🤣\n請再試一次😌"
    if len(event_name) > 20:
        return "事件名稱不可以超過 20 字元🤣\n請再試一次😌"
    invalid_chars = re.findall(r"[^\u4e00-\u9fffA-Za-z0-9 _-]", event_name)
    if invalid_chars:
        invalid_chars = list(dict.fromkeys(invalid_chars))
        wrapped = "、".join([f"「{ch}」" for ch in invalid_chars])
        return f"無效的字元：{wrapped}\n請再試一次😌"
    return None


def parse_event_cycle(msg: str) -> tuple[int, str] | None:
    try:
        value, unit = msg.split(" ", maxsplit=1)
    except ValueError:
        return None
    try:
        value = int(value)
    except ValueError:
        return None
    if unit not in enums.SUPPORTED_UNITS:
        return None
    return value, unit


# ------------------------------ Chat Handlers ------------------------------- #


def handle_new_event_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == enums.NewEventSteps.INPUT_NAME:
        logger.debug("Processing event name input")
        event_name = msg

        # validate event name
        error_msg = validate_event_name(event_name)
        if error_msg is not None:
            logger.debug(f"Invalid event name input: {event_name}")
            return TextMessage(text=error_msg)
        if db.get_event_id(chat.user_id, event_name, conn) is not None:
            logger.debug(f"Duplicated event name input: {event_name}")
            return msg.Error.event_name_duplicated(event_name)

        chat.payload["event_name"] = event_name
        chat.payload["chat_id"] = chat.chat_id
        logger.info(f"Added to chat payload: event_name='{event_name}'")
        logger.info(f"Added to chat payload: chat_id='{chat.chat_id}'")
        db.set_chat_payload(chat.chat_id, chat.payload, conn)
        db.set_chat_current_step(chat.chat_id, enums.NewEventSteps.INPUT_START_DATE.value, conn)
        return msg.NewEvent.prompt_for_start_date(chat.payload)

    elif chat.current_step == enums.NewEventSteps.INPUT_START_DATE:
        logger.debug("Text input is not expected at current step")
        return msg.NewEvent.invalid_input_for_start_date(chat.payload)

    elif chat.current_step == enums.NewEventSteps.INPUT_ENABLE_REMINDER:
        logger.info("Processing enable reminder input")
        if msg == "設定提醒":
            chat.payload["reminder_enabled"] = True
            logger.info("Added to chat payload: reminder_enabled=True")
            db.set_chat_payload(chat.chat_id, chat.payload, conn)
            db.set_chat_current_step(chat.chat_id, enums.NewEventSteps.INPUT_EVENT_CYCLE.value, conn)
            return msg.NewEvent.prompt_for_event_cycle(chat.payload)
        elif msg == "不設定提醒":
            chat.payload["reminder_enabled"] = False
            logger.info("Added to chat payload: reminder_enabled=False")
            db.set_chat_current_step(chat.chat_id, None, conn)
            db.set_chat_status(chat.chat_id, enums.ChatStatus.COMPLETED.value, conn)
            logger.info(f"Chat completed: {chat.chat_id}")

            event_id = str(uuid.uuid4())
            event = EventData(
                event_id=event_id,
                event_name=chat.payload["event_name"],
                user_id=chat.user_id,
                last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
                reminder_enabled=False,
            )
            db.add_event(event, conn)
            update = UpdateData(
                update_id=str(uuid.uuid4()),
                event_id=event_id,
                event_name=chat.payload["event_name"],
                user_id=chat.user_id,
                done_at=datetime.fromisoformat(chat.payload["start_date"]),
            )
            db.add_update(update, conn)
            db.increment_user_event_count(chat.user_id, by=1, conn=conn)
            return msg.NewEvent.event_created_no_reminder(chat.payload)
        else:
            logger.debug(f"Invalid enable reminder input: {msg}")
            return msg.NewEvent.invalid_input_for_enable_reminder(chat.payload)

    elif chat.current_step == enums.NewEventSteps.INPUT_EVENT_CYCLE:
        logger.info("Processing event cycle input")
        if msg.lower() == "example":
            logger.info("Return event cycle example")
            return msg.NewEvent.event_cycle_example()
        if parse_event_cycle(msg) is None:
            logger.info(f"Invalid event cycle input: {msg}")
            return msg.NewEvent.invalid_input_for_event_cycle(chat.payload)
        chat.payload["event_cycle"] = msg
        increment, unit = parse_event_cycle(msg)
        start_date = datetime.fromisoformat(chat.payload["start_date"])

        if unit == enums.CycleUnit.DAY:
            offset = relativedelta(days=+increment)
        elif unit == enums.CycleUnit.WEEK:
            offset = relativedelta(weeks=+increment)
        elif unit == enums.CycleUnit.MONTH:
            offset = relativedelta(months=+increment)
        next_due_at = start_date + offset
        logger.info(f"Added to chat payload: event_cycle='{chat.payload['event_cycle']}'")
        logger.info(f"Next due at: {next_due_at.strftime('%Y-%m-%d')}")
        db.set_chat_payload(chat.chat_id, chat.payload, conn)
        db.set_chat_current_step(chat.chat_id, None, conn)
        db.set_chat_status(chat.chat_id, enums.ChatStatus.COMPLETED.value, conn)
        logger.info(f"Chat completed: {chat.chat_id}")

        event_id = str(uuid.uuid4())
        event = EventData(
            event_id=event_id,
            event_name=chat.payload["event_name"],
            user_id=chat.user_id,
            last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
            reminder_enabled=True,
            event_cycle=chat.payload["event_cycle"],
            next_due_at=next_due_at,
        )
        db.add_event(event, conn)
        update = UpdateData(
            update_id=str(uuid.uuid4()),
            event_id=event_id,
            event_name=chat.payload["event_name"],
            user_id=chat.user_id,
            done_at=datetime.fromisoformat(chat.payload["start_date"]),
        )
        db.add_update(update, conn)
        db.increment_user_event_count(chat.user_id, by=1, conn=conn)
        return msg.NewEvent.event_created_with_reminder(chat.payload)


def handle_find_event_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == enums.FindEventSteps.INPUT_NAME:
        logger.info("Processing event name input")
        event_name = msg

        error_msg = validate_event_name(event_name)
        if error_msg is not None:
            logger.info(f"Invalid event name input: {event_name}")
            return TextMessage(text=error_msg)
        event_id = db.get_event_id(chat.user_id, event_name, conn)
        if event_id is None:
            logger.info(f"Event name not found: {event_name}")
            return msg.Error.event_name_not_found(event_name)

        logger.info(f"Event name input: {event_name}")
        logger.info(f"Event found: {event_id}")
        event = db.get_event(event_id, conn)
        recent_update_times = db.list_event_recent_update_times(event_id, conn)
        db.set_chat_current_step(chat.chat_id, None, conn)
        db.set_chat_status(chat.chat_id, enums.ChatStatus.COMPLETED.value, conn)
        logger.info(f"Chat completed: {chat.chat_id}")
        return msg.FindEvent.format_event_summary(event, recent_update_times)


def create_new_chat(command: str, user_id: str, conn: psycopg.Connection) -> Message:
    chat_id = str(uuid.uuid4())
    if command == enums.Command.NEW:
        user = db.get_user(user_id, conn)
        if user.is_limited:
            logger.info("Failed to create new event: reached max events allowed")
            return msg.Error.max_events_reached()
        logger.info("Creating new chat, chat type: new event")
        chat = ChatData(
            chat_id=chat_id,
            user_id=user_id,
            chat_type=enums.ChatType.NEW_EVENT.value,
            current_step=enums.NewEventSteps.INPUT_NAME.value,
        )
        db.add_chat(chat, conn)
        return msg.NewEvent.prompt_for_event_name()

    if command == enums.Command.FIND:
        logger.info("Creating new chat, chat type: find event")
        chat = ChatData(
            chat_id=chat_id,
            user_id=user_id,
            chat_type=enums.ChatType.FIND_EVENT.value,
            current_step=enums.FindEventSteps.INPUT_NAME.value,
        )
        db.add_chat(chat, conn)
        return msg.FindEvent.prompt_for_event_name()

    if command == enums.Command.SETTINGS:
        logger.info("Creating new chat, chat type: user settings")
        chat = ChatData(
            chat_id=chat_id,
            user_id=user_id,
            chat_type=enums.ChatType.USER_SETTINGS.value,
            current_step=enums.UserSettingsSteps.INPUT_OPTION.value,
        )
        db.add_chat(chat, conn)
        return


def handle_ongoing_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.chat_type == enums.ChatType.NEW_EVENT:
        return handle_new_event_chat(msg, chat, conn)
    if chat.chat_type == enums.ChatType.FIND_EVENT:
        return handle_find_event_chat(msg, chat, conn)


def get_reply_message(msg: str, user_id: str) -> Message:
    logger.debug(f"Message received: {msg}")
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        ongoing_chat_id = db.get_ongoing_chat_id(user_id, conn)

        if ongoing_chat_id is None:
            if msg == enums.Command.ABORT:
                return msg.Abort.no_ongoing_chat()
            if not msg.startswith("/"):
                return msg.Greeting.random()
            if msg not in enums.SUPPORTED_COMMANDS:
                return msg.Error.unrecognized_command()
            return create_new_chat(msg, user_id, conn)

        chat = db.get_chat(ongoing_chat_id, conn)
        logger.debug(f"Ongoing chat found: {chat.chat_id}")
        logger.debug(f"Chat type: {chat.chat_type}")
        logger.debug(f"Current step: {chat.current_step}")

        if msg == enums.Command.ABORT:
            chat.status = enums.ChatStatus.ABORTED.value
            db.set_chat_status(chat.chat_id, enums.ChatStatus.ABORTED.value, conn)
            logger.info(f"Chat aborted: {chat.chat_id}")
            return msg.Abort.ongoing_chat_aborted()

        return handle_ongoing_chat(msg, chat, conn)


# --------------------------- LINE Event Handlers ---------------------------- #


@handler.add(FollowEvent)
def handle_user_added(event: FollowEvent) -> None:
    user_id = event.source.user_id

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        if not db.user_exists(user_id, conn):
            logger.info(f"Added by: {user_id}")
            db.add_user(user_id, conn)
        else:
            logger.info(f"Unblocked by: {user_id}")
            db.set_user_activeness(user_id, True, conn)
            db.set_event_activeness_by_user(user_id, True, conn)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="hello my new friend!")])
        )


@handler.add(UnfollowEvent)
def handle_user_blocked(event: UnfollowEvent) -> None:
    user_id = event.source.user_id
    logger.info(f"Blocked by: {user_id}")

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        if not db.user_exists(user_id, conn):
            logger.warning("User not found in database")
        else:
            db.set_user_activeness(user_id, False, conn)
            db.set_event_activeness_by_user(user_id, False, conn)


@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent) -> None:
    logger.info(f"Postback data: {event.postback.data}")
    logger.info(f"Postback params: {event.postback.params}")
    chat_id = event.postback.data
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        chat = db.get_chat(chat_id, conn)
        # only proceed if status and current step matches
        if chat.chat_type == enums.ChatType.NEW_EVENT and chat.current_step == enums.NewEventSteps.INPUT_START_DATE:
            logger.info("Processing start date input")
            start_date = datetime.strptime(event.postback.params["date"], "%Y-%m-%d")
            start_date = start_date.replace(tzinfo=TZ_TAIPEI)
            chat.payload["start_date"] = start_date.isoformat()  # datetime is not JSON serializable
            chat.current_step = enums.NewEventSteps.INPUT_ENABLE_REMINDER
            logger.info(f"Added to chat payload: start_date='{chat.payload['start_date']}'")
            db.set_chat_payload(chat.chat_id, chat.payload, conn)
            db.set_chat_current_step(chat.chat_id, enums.NewEventSteps.INPUT_ENABLE_REMINDER.value, conn)
            reply_msg = msg.NewEvent.prompt_for_toggle_reminder(chat.payload)
        else:
            return None

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_msg]))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    msg = sanitize_msg(event.message.text)
    reply_msg = get_reply_message(msg=msg, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_msg]))
