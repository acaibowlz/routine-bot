from datetime import datetime

from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import FlexMessage

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import flex_bubble_template, parse_time_delta
from routine_bot.models import EventData


def user_owned_event(event: EventData) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"Event {event.event_id} has reminder enabled, but the next due date cannot be found")
    time_delta = relativedelta(datetime.now(TZ_TAIPEI), event.next_due_at)
    overdue_by = parse_time_delta(time_delta)

    lines = [
        f"✅ 上次完成：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 事件週期：{event.event_cycle}",
    ]
    if not overdue_by:
        lines.append(f"🗓️ 下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
        alt_text = f"⏰ 溫馨提醒～［{event.event_name}］已到預定的下次日期"
    else:
        lines.append(f"🗓️ 原定下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已超過原定間隔：{overdue_by}")
        alt_text = f"⏰ 溫馨提醒～［{event.event_name}］已超過原定間隔 {overdue_by}"

    bubble = flex_bubble_template(
        title=f"⏰ 是時候安排下次的［{event.event_name}］了！",
        lines=lines,
    )
    msg = FlexMessage(altText=alt_text, contents=bubble)
    return msg


def shared_event(event: EventData, owner_profile: dict[str, str]) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"Event {event.event_id} has reminder enabled, but the next due date cannot be found")
    time_delta = relativedelta(datetime.now(TZ_TAIPEI), event.next_due_at)
    overdue_by = parse_time_delta(time_delta)

    lines = [
        f"🫂 來自共享：{owner_profile.get('displayName')}",
        f"✅ 上次完成：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 事件週期：{event.event_cycle}",
    ]
    if not overdue_by:
        lines.append(f"🗓️ 下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
        alt_text = f"⏰ 溫馨提醒～［{event.event_name}］（來自{owner_profile.get('displayName')}）已到下次預計時間"
    else:
        lines.append(f"🗓️ 原定下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已超過原定間隔：{overdue_by}")
        alt_text = (
            f"⏰ 溫馨提醒～［{event.event_name}］（來自{owner_profile.get('displayName')}）已超過原定間隔 {overdue_by}"
        )

    bubble = flex_bubble_template(
        title=f"⏰ 是時候安排下次的［{event.event_name}］了！",
        lines=lines,
    )
    msg = FlexMessage(altText=alt_text, contents=bubble)
    return msg
