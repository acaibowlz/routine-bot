import logging

import psycopg
from linebot.v3.messaging import FlexMessage

import routine_bot.db.events as event_db
import routine_bot.messages as msg
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def handle_view_all_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    events = event_db.list_events_by_user(user_id, conn)
    logger.info(f"Retrieved {len(events)} events for user_id: {user_id}")
    return msg.events.view_all.format_all_events_summary(events)
