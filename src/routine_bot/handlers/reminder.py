import logging
from datetime import datetime

import psycopg
from linebot.v3.messaging import MessagingApi, PushMessageRequest

import routine_bot.db.events as event_db
import routine_bot.db.shares as share_db
import routine_bot.messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.utils import format_logger_name, get_time_diff, get_user_profile

logger = logging.getLogger(format_logger_name(__name__))


def send_reminders_for_user_owned_events(user_id: str, line_bot_api: MessagingApi, conn: psycopg.Connection) -> int:
    events = event_db.list_overdue_events_by_user(user_id, conn)
    if not len(events):
        logger.info("No overdue event found")
        return 0

    logger.info(f"Found {len(events)} overdue events")
    for event in events:
        payload = {}
        payload["event_name"] = event.event_name
        payload["event_cycle"] = event.event_cycle
        payload["last_done_at"] = event.last_done_at.strftime("%Y-%m-%d")
        if event.next_due_at is not None:
            payload["time_diff"] = get_time_diff(datetime.now(), event.next_due_at)
            payload["next_due_at"] = event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime("%Y-%m-%d")
        push_msg = msg.reminder.user_owned_event(payload)
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[push_msg]))
        logger.info(f"Sent reminder for event: {event.event_id}")
    return len(events)


def send_reminders_for_shared_events(user_id: str, line_bot_api: MessagingApi, conn: psycopg.Connection) -> int:
    events = share_db.list_overdue_shared_events_by_user(user_id, conn)
    if not len(events):
        logger.info("No overdue shared event found")
        return 0

    logger.info(f"Found: {len(events)} overdue shared events")
    for event in events:
        payload = {}
        owner_profile = get_user_profile(event.user_id)
        payload["owner_name"] = owner_profile.display_name
        payload["event_name"] = event.event_name
        payload["event_cycle"] = event.event_cycle
        payload["last_done_at"] = event.last_done_at.strftime("%Y-%m-%d")
        if event.next_due_at is not None:
            payload["time_diff"] = get_time_diff(datetime.now(), event.next_due_at)
            payload["next_due_at"] = event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime("%Y-%m-%d")
        push_msg = msg.reminder.shared_event(event, owner_profile.display_name)
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[push_msg]))
        logger.info(f"Sent reminder for event: {event.event_id}")
    return len(events)
