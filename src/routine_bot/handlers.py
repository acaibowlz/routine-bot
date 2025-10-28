import logging
import re
import unicodedata
import uuid
from datetime import datetime
from pprint import pformat

import psycopg
import requests
from cachetools.func import ttl_cache
from dateutil.relativedelta import relativedelta
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexMessage,
    Message,
    MessagingApi,
    ReplyMessageRequest,
    TemplateMessage,
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


def sanitize_msg(text: str) -> str:
    """
    Cleans and normalizes user input text for consistent downstream processing.

    Steps:
    1. Trim leading/trailing whitespace and newlines
    2. Normalize Unicode (NFKC) — converts fullwidth to halfwidth, etc.
    3. Collapse multiple spaces/newlines
    4. Remove invisible control characters
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
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


def parse_event_cycle(text: str) -> tuple[int, str] | None:
    try:
        value, unit = text.split(" ", maxsplit=1)
    except ValueError:
        return None
    try:
        value = int(value)
    except ValueError:
        return None
    if unit not in enums.SUPPORTED_UNITS:
        return None
    return value, unit


# ------------------------------ Step Processors ------------------------------ #


def process_new_event_input_name(text: str, chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Processing new event name input")
    event_name = text

    # validate event name
    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name input: {event_name}")
        return TextMessage(text=error_msg)
    if db.get_event_id(chat.user_id, event_name, conn) is not None:
        logger.info(f"Duplicated event name input: {event_name}")
        return msg.Error.event_name_duplicated(event_name)

    chat.payload["event_name"] = event_name
    chat.payload["chat_id"] = chat.chat_id
    chat.current_step = enums.NewEventSteps.SELECT_START_DATE.value
    db.set_chat_payload(chat.chat_id, chat.payload, conn)
    db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Added to payload: event_name={event_name}")
    logger.info(f"Added to payload: chat_id={chat.chat_id}")
    logger.info(f"Current step updated: {chat.current_step}")
    return msg.NewEvent.select_start_date(chat.payload)


def process_new_event_select_start_date(postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection):
    logger.info("Processing start date selection")
    start_date = datetime.strptime(postback.postback.params["date"], "%Y-%m-%d")
    start_date = start_date.replace(tzinfo=TZ_TAIPEI)
    chat.payload["start_date"] = start_date.isoformat()  # datetime is not JSON serializable
    chat.current_step = enums.NewEventSteps.ENABLE_REMINDER
    logger.info(f"Added to payload: start_date={chat.payload['start_date']}")
    db.set_chat_payload(chat.chat_id, chat.payload, conn)
    db.set_chat_current_step(chat.chat_id, enums.NewEventSteps.ENABLE_REMINDER.value, conn)
    return msg.NewEvent.enable_reminder(chat.payload)


def process_new_event_enable_reminder(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Processing enable reminder")
    chat.payload["reminder_enabled"] = True
    chat.current_step = enums.NewEventSteps.SELECT_EVENT_CYCLE.value
    db.set_chat_payload(chat.chat_id, chat.payload, conn)
    db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info("Added to payload: reminder_enabled=True")
    logger.info(f"Current step updated: {chat.current_step}")
    return msg.NewEvent.select_event_cycle(chat.payload)


def process_new_event_disable_reminder(chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    logger.info("Processing disable reminder")
    chat.payload["reminder_enabled"] = False
    chat.current_step = None
    chat.status = enums.ChatStatus.COMPLETED.value
    db.set_chat_payload(chat.chat_id, chat.payload, conn)
    db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    db.set_chat_status(chat.chat_id, chat.status, conn)
    logger.info("Added to payload: reminder_enabled=False")
    logger.info(f"Current step updated: {chat.current_step}")
    logger.info("Chat completed")

    event_id = str(uuid.uuid4())
    event = EventData(
        event_id=event_id,
        user_id=chat.user_id,
        event_name=chat.payload["event_name"],
        reminder_enabled=False,
        event_cycle=None,
        last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
        next_due_at=None,
        share_count=0,
        is_active=True,
    )
    db.add_event(event, conn)
    logger.info("┌── New Event Created ──────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info("└───────────────────────────────────────────")

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


def process_new_event_select_event_cycle(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    logger.info("Processing event cycle input")
    if text.lower() == "example":
        logger.info("Showing event cycle example")
        return msg.NewEvent.event_cycle_example()
    if parse_event_cycle(text) is None:
        logger.info(f"Invalid event cycle input: {text}")
        return msg.NewEvent.invalid_input_for_event_cycle(chat.payload)
    chat.payload["event_cycle"] = text
    increment, unit = parse_event_cycle(text)
    start_date = datetime.fromisoformat(chat.payload["start_date"])

    if unit == enums.CycleUnit.DAY:
        offset = relativedelta(days=+increment)
    elif unit == enums.CycleUnit.WEEK:
        offset = relativedelta(weeks=+increment)
    elif unit == enums.CycleUnit.MONTH:
        offset = relativedelta(months=+increment)
    next_due_at = start_date + offset

    chat.payload["next_due_at"] = next_due_at.isoformat()
    chat.current_step = None
    chat.status = enums.ChatStatus.COMPLETED.value
    db.set_chat_payload(chat.chat_id, chat.payload, conn)
    db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    db.set_chat_status(chat.chat_id, chat.status, conn)
    logger.info(f"Added to payload: next_due_at={next_due_at}")
    logger.info(f"Current step updated: {chat.current_step}")
    logger.info("Chat completed")

    event_id = str(uuid.uuid4())
    event = EventData(
        event_id=event_id,
        user_id=chat.user_id,
        event_name=chat.payload["event_name"],
        reminder_enabled=True,
        event_cycle=chat.payload["event_cycle"],
        last_done_at=start_date,
        next_due_at=next_due_at,
        share_count=0,
        is_active=True,
    )
    db.add_event(event, conn)
    logger.info("┌── New Event Created ──────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User: {event.user_id}")
    logger.info(f"│ Name: {event.event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Cycle: {event.event_cycle}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info(f"│ Next Due: {event.next_due_at}")
    logger.info("└───────────────────────────────────────────")

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


def process_find_event_input_name(text: str, chat: ChatData, conn: psycopg.Connection) -> FlexMessage:
    logger.info("Processing find event name input")
    event_name = text

    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name input: {event_name}")
        return TextMessage(text=error_msg)
    event_id = db.get_event_id(chat.user_id, event_name, conn)
    if event_id is None:
        logger.info(f"Event name not found: {event_name}")
        return msg.Error.event_name_not_found(event_name)

    event = db.get_event(event_id, conn)
    recent_update_times = db.list_event_recent_update_times(event_id, conn)
    logger.info("┌── Event Found ────────────────────────────")
    logger.info(f"│ ID: {event_id}")
    logger.info(f"│ User ID: {event.user_id}")
    logger.info(f"│ Name: {event_name}")
    logger.info(f"│ Reminder: {event.reminder_enabled}")
    logger.info(f"│ Cycle: {event.event_cycle}")
    logger.info(f"│ Last Done: {event.last_done_at}")
    logger.info(f"│ Next Due: {event.next_due_at}")
    logger.info(f"│ Recent Updates: {len(recent_update_times)}")
    logger.info("└───────────────────────────────────────────")

    chat.current_step = None
    chat.status = enums.ChatStatus.COMPLETED.value
    db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    db.set_chat_status(chat.chat_id, chat.status, conn)
    logger.info(f"Current step updated: {chat.current_step}")
    logger.info("Chat completed")
    return msg.FindEvent.format_event_summary(event, recent_update_times)


def prepare_user_settings_new_notification_selection(chat: ChatData, conn: psycopg.Connection) -> TemplateMessage:
    logger.info("Option selected: new notification slot")
    option = enums.UserSettingsOptions.NOTIFICATION_SLOT.value
    user = db.get_user(chat.user_id, conn)
    chat.payload["option"] = option
    chat.payload["chat_id"] = chat.chat_id
    chat.payload["current_slot"] = user.notification_slot.strftime("%H:%M")
    chat.current_step = enums.UserSettingsSteps.SELECT_NEW_NOTIFICATION_SLOT.value
    db.set_chat_payload(chat.chat_id, chat.payload, conn)
    db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Added to payload: option={option}")
    logger.info(f"Added to payload: chat_id={chat.chat_id}")
    logger.info(f"Added to payload: current_slot={chat.payload['current_slot']}")
    logger.info(f"Current step updated: {chat.current_step}")
    return msg.UserSettings.select_new_notification_slot(chat.payload)


def process_user_settings_select_new_notification_slot(
    postback: PostbackEvent, chat: ChatData, conn: psycopg.Connection
):
    logger.info("Processing new notification slot selection")
    if postback.postback.params["time"].split(":")[1] != "00":
        return msg.UserSettings.invalid_notification_slot(chat.payload)
    else:
        time_slot = postback.postback.params["time"]
        chat.payload["new_slot"] = time_slot
        db.set_chat_payload(chat.chat_id, chat.payload, conn)
        db.set_chat_current_step(chat.chat_id, None, conn)
        db.set_chat_status(chat.chat_id, enums.ChatStatus.COMPLETED.value, conn)
        logger.info(f"Added to chat payload: new_slot='{chat.payload['new_slot']}'")
        logger.info(f"Current step updated: {chat.current_step}")
        logger.info("Chat completed")
        time_slot = datetime.strptime(time_slot, "%H:%M")
        db.set_user_notification_slot(chat.user_id, time_slot, conn)
        return msg.UserSettings.notification_slot_updated(chat.payload)


def process_delete_event_input_name(text: str, chat: ChatData, conn: psycopg.Connection):
    logger.info("Process delete event name input")
    event_name = text

    error_msg = validate_event_name(event_name)
    if error_msg is not None:
        logger.info(f"Invalid event name input: {event_name}")
        return TextMessage(text=error_msg)
    event_id = db.get_event_id(chat.user_id, event_name, conn)
    if event_id is None:
        logger.info(f"Event name not found: {event_name}")
        return msg.Error.event_name_not_found(event_name)

    event = db.get_event(event_id, conn)
    chat.payload["event_id"] = event_id
    chat.current_step = enums.DeleteEventSteps.CONFIRM_DELETION.value
    db.set_chat_payload(chat.chat_id, chat.payload, conn)
    db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
    logger.info(f"Added to payload: event_id={event_id}")
    logger.info(f"Current step updated: {chat.current_step}")
    return msg.DeleteEvent.comfirm_event_deletion(event)


def process_delete_event_confirm_deletion(text: str, chat: ChatData, conn: psycopg.Connection):
    logger.info("Processing delete event confirm deletion")
    event_id = chat.payload["event_id"]
    event = db.get_event(event_id, conn)
    if text == "刪除事件":
        chat.payload["confirmation"] = True
        chat.current_step = None
        chat.status = enums.ChatStatus.COMPLETED.value
        db.set_chat_payload(chat.chat_id, chat.payload, conn)
        db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
        db.set_chat_status(chat.chat_id, chat.status, conn)
        logger.info("Added to chat payload: confirmation=True")
        logger.info(f"Current step updated: {chat.current_step}")
        logger.info("Chat completed")

        db.delete_updates_by_event_id(event_id, conn)
        db.delete_event(event_id, conn)
        logger.info("┌── Event Deleted ──────────────────────────")
        logger.info(f"│ ID: {event.event_id}")
        logger.info(f"│ User: {event.user_id}")
        logger.info(f"│ Name: {event.event_name}")
        logger.info("└───────────────────────────────────────────")
        return msg.DeleteEvent.deleted(event.event_name)
    elif text == "取消刪除":
        chat.payload["confirmation"] = False
        chat.current_step = None
        chat.status = enums.ChatStatus.COMPLETED.value
        db.set_chat_payload(chat.chat_id, chat.payload, conn)
        db.set_chat_current_step(chat.chat_id, chat.current_step, conn)
        db.set_chat_status(chat.chat_id, chat.status, conn)
        logger.info("Added to chat payload: confirmation=False")
        logger.info(f"Current step updated: {chat.current_step}")
        logger.info("Chat completed")
        logger.info("Deletion cancelled")
        return msg.DeleteEvent.cancelled(event.event_name)
    else:
        logger.info(f"Invalid delete confirmation input: {text}")
        event = db.get_event(chat.payload["event_id"], conn)
        return msg.DeleteEvent.invalid_delete_confirmation(event)


# ----------------------------- New Chat Creators ----------------------------- #


def create_new_event_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage | TextMessage:
    user = db.get_user(user_id, conn)
    if user.is_limited:
        logger.info("Failed to create new event: reached max events allowed")
        return msg.Error.max_events_reached()
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: new event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=enums.ChatType.NEW_EVENT.value,
        current_step=enums.NewEventSteps.INPUT_NAME.value,
        payload={},
        status=enums.ChatStatus.ONGOING.value,
    )
    db.add_chat(chat, conn)
    return msg.NewEvent.prompt_for_event_name()


def create_find_event_chat(user_id: str, conn: psycopg.Connection) -> TextMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: find event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=enums.ChatType.FIND_EVENT.value,
        current_step=enums.FindEventSteps.INPUT_NAME.value,
        payload={},
        status=enums.ChatStatus.ONGOING.value,
    )
    db.add_chat(chat, conn)
    return msg.FindEvent.prompt_for_event_name()


def create_user_settings_chat(user_id: str, conn: psycopg.Connection) -> TemplateMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: user settings")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=enums.ChatType.USER_SETTINGS.value,
        current_step=enums.UserSettingsSteps.SELECT_OPTION.value,
        payload={},
        status=enums.ChatStatus.ONGOING.value,
    )
    db.add_chat(chat, conn)
    return msg.UserSettings.select_option()


def create_delete_event_chat(user_id: str, conn: psycopg.Connection) -> TextMessage:
    chat_id = str(uuid.uuid4())
    logger.info("Creating new chat, chat type: delete event")
    logger.info(f"Chat ID: {chat_id}")
    chat = ChatData(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=enums.ChatType.DELETE_EVENT.value,
        current_step=enums.DeleteEventSteps.INPUT_NAME.value,
        payload={},
        status=enums.ChatStatus.ONGOING.value,
    )
    db.add_chat(chat, conn)
    return msg.DeleteEvent.prompt_for_event_name()


# ------------------------------ Chat Handlers ------------------------------- #


def handle_new_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == enums.NewEventSteps.INPUT_NAME:
        return process_new_event_input_name(text, chat, conn)
    elif chat.current_step == enums.NewEventSteps.SELECT_START_DATE:
        logger.info("Text input is not expected at current step")
        return msg.NewEvent.invalid_input_for_start_date(chat.payload)
    elif chat.current_step == enums.NewEventSteps.ENABLE_REMINDER:
        if text == "設定提醒":
            return process_new_event_enable_reminder(chat, conn)
        elif text == "不設定提醒":
            return process_new_event_disable_reminder(chat, conn)
        else:
            logger.info(f"Invalid enable reminder input: {text}")
            return msg.NewEvent.invalid_input_for_enable_reminder(chat.payload)
    elif chat.current_step == enums.NewEventSteps.SELECT_EVENT_CYCLE:
        return process_new_event_select_event_cycle(text, chat, conn)
    else:
        logger.error(f"Unexpected step in handle_new_event_chat: {chat.current_step}")
        return msg.Error.unexpected_error()


def handle_find_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == enums.FindEventSteps.INPUT_NAME:
        return process_find_event_input_name(text, chat, conn)
    else:
        logger.error(f"Unexpected step in handle_find_event_chat: {chat.current_step}")
        return msg.Error.unexpected_error()


def handle_user_settings_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == enums.UserSettingsSteps.SELECT_OPTION:
        logger.info("Processing user settings option input")
        if text == "更改提醒時段":
            return prepare_user_settings_new_notification_selection(chat, conn)
        else:
            logger.info(f"Invalid user settings option input: {text}")
            return msg.UserSettings.invalid_input_for_option()
    elif chat.current_step == enums.UserSettingsSteps.SELECT_NEW_NOTIFICATION_SLOT:
        logger.info("Text input is not expected at current step")
        return msg.UserSettings.invalid_input_for_notification_slot(chat.payload)
    else:
        logger.error(f"Unexpected step in handle_user_settings_chat: {chat.current_step}")
        return msg.UserSettings.unexpected_error()


def handle_delete_event_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.current_step == enums.DeleteEventSteps.INPUT_NAME:
        return process_delete_event_input_name(text, chat, conn)
    elif chat.current_step == enums.DeleteEventSteps.CONFIRM_DELETION:
        return process_delete_event_confirm_deletion(text, chat, conn)
    else:
        logger.error(f"Unexpected step in handle_delete_event_chat: {chat.current_step}")
        return msg.UserSettings.unexpected_error()


def handle_new_chat(text: str, user_id: str, conn: psycopg.Connection) -> Message:
    if text == enums.Command.NEW:
        return create_new_event_chat(user_id, conn)
    elif text == enums.Command.FIND:
        return create_find_event_chat(user_id, conn)
    elif text == enums.Command.SETTINGS:
        return create_user_settings_chat(user_id, conn)
    elif text == enums.Command.DELETE:
        return create_delete_event_chat(user_id, conn)
    else:
        logger.error(f"Unexpected command in handle_new_chat: {text}")
        return msg.Error.unexpected_error()


def handle_ongoing_chat(text: str, chat: ChatData, conn: psycopg.Connection) -> Message:
    if chat.chat_type == enums.ChatType.NEW_EVENT:
        return handle_new_event_chat(text, chat, conn)
    elif chat.chat_type == enums.ChatType.FIND_EVENT:
        return handle_find_event_chat(text, chat, conn)
    elif chat.chat_type == enums.ChatType.USER_SETTINGS:
        return handle_user_settings_chat(text, chat, conn)
    elif chat.chat_type == enums.ChatType.DELETE_EVENT:
        return handle_delete_event_chat(text, chat, conn)
    else:
        logger.error(f"Unexpected chat type in handle_ongoing_chat: {chat.chat_type}")
        return msg.Error.unexpected_error()


def get_reply_message(text: str, user_id: str) -> Message:
    logger.info(f"Message received: {text}")
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        ongoing_chat_id = db.get_ongoing_chat_id(user_id, conn)

        if ongoing_chat_id is None:
            if text == enums.Command.ABORT:
                return msg.Abort.no_ongoing_chat()
            if not text.startswith("/"):
                return msg.Greeting.random()
            if text not in enums.SUPPORTED_COMMANDS:
                return msg.Error.unrecognized_command()
            return handle_new_chat(text, user_id, conn)

        chat = db.get_chat(ongoing_chat_id, conn)
        logger.info(f"Ongoing chat found: {chat.chat_id}")
        logger.info(f"Chat type: {chat.chat_type}")
        logger.info(f"Current step: {chat.current_step}")

        if text == enums.Command.ABORT:
            chat.status = enums.ChatStatus.ABORTED.value
            db.set_chat_status(chat.chat_id, enums.ChatStatus.ABORTED.value, conn)
            logger.info("Chat aborted")
            return msg.Abort.ongoing_chat_aborted()

        return handle_ongoing_chat(text, chat, conn)


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
    logger.debug(f"Postback data: {event.postback.data}")
    logger.debug(f"Postback params: {event.postback.params}")
    chat_id = event.postback.data
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        chat = db.get_chat(chat_id, conn)
        # only proceed if status and current step matches
        if chat.chat_type == enums.ChatType.NEW_EVENT and chat.current_step == enums.NewEventSteps.SELECT_START_DATE:
            reply_msg = process_new_event_select_start_date(event, chat, conn)
        elif (
            chat.chat_type == enums.ChatType.USER_SETTINGS
            and chat.current_step == enums.UserSettingsSteps.SELECT_NEW_NOTIFICATION_SLOT
        ):
            reply_msg = process_user_settings_select_new_notification_slot(event, chat, conn)
        else:
            return None

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_msg]))


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    text = sanitize_msg(event.message.text)
    reply_msg = get_reply_message(text=text, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[reply_msg]))
