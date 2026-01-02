import logging
from datetime import datetime

import psycopg
from linebot.v3.messaging import FlexMessage

import routine_bot.db.events as event_db
import routine_bot.db.shares as share_db
import routine_bot.messages as msg
from routine_bot.constants import TZ_TAIPEI
from routine_bot.utils import format_logger_name, get_time_diff, get_user_profile

logger = logging.getLogger(format_logger_name(__name__))


def handle_view_all_chat(user_id: str, conn: psycopg.Connection) -> FlexMessage:
    user_events = event_db.list_events_by_user(user_id, conn)
    logger.info(f"Retrieved {len(user_events)} events for user: {user_id}")
    shared_events = share_db.list_shared_events_by_user(user_id, conn)
    logger.info(f"Retrieved {len(shared_events)} shared events for user: {user_id}")
    all_events = user_events + shared_events

    event_summaries = []
    for event in all_events:
        new_entry = {}
        new_entry["event_name"] = event.event_name
        if event.user_id != user_id:
            owner_profile = get_user_profile(event.user_id)
            new_entry["owner_name"] = owner_profile.display_name
        else:
            new_entry["owner_name"] = ""
        now = datetime.today().astimezone(TZ_TAIPEI)
        last_done_at = event.last_done_at.astimezone(tz=TZ_TAIPEI)
        new_entry["time_diff"] = get_time_diff(now, last_done_at)
        if event.reminder_enabled and event.next_due_at is not None:
            new_entry["next_reminder"] = event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime("%Y-%m-%d")
        else:
            new_entry["next_reminder"] = ""
        event_summaries.append(new_entry)

    payload = {"event_summaries": str(event_summaries)}
    logger.debug(payload)
    return msg.events.view_all.format_all_events_summary(payload)
