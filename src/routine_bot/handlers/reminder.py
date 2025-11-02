import logging

import psycopg
from linebot.v3.messaging import MessagingApi, PushMessageRequest

import routine_bot.db.events as event_db
import routine_bot.db.shares as share_db
import routine_bot.messages as msg
from routine_bot.utils import format_logger_name, get_user_profile

logger = logging.getLogger(format_logger_name(__name__))


def send_reminders_for_user_owned_events(user_id: str, line_bot_api: MessagingApi, conn: psycopg.Connection) -> None:
    events = event_db.list_overdue_events_by_user(user_id, conn)
    if not len(events):
        logger.info("No overdue event found")
        return
    logger.info(f"{len(events)} overdue events found")
    for event in events:
        push_msg = msg.reminder.user_owned_event(event)
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[push_msg]))
        logger.info(f"Notification sent: {event.event_id}")


def send_reminders_for_shared_events(user_id: str, line_bot_api: MessagingApi, conn: psycopg.Connection) -> None:
    events = share_db.list_overdue_shared_events_by_user(user_id, conn)
    if not len(events):
        logger.info("No overdue shared event found")
        return
    logger.info(f"{len(events)} overdue shared events found")
    for event in events:
        owner_profile = get_user_profile(event.user_id)
        push_msg = msg.reminder.shared_event(event, owner_profile)
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[push_msg]))
        logger.info(f"Notification sent: {event.event_id}")
