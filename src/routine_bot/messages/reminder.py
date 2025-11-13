from datetime import datetime

from linebot.v3.messaging import FlexMessage

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import flex_bubble_template, get_verbal_time_diff
from routine_bot.models import EventData


def user_owned_event(event: EventData) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"The event '{event.event_name}' does not have a valid next due date.")

    title = f"🍞 又該{event.event_name}囉～"
    lines = [
        f"🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 重複週期：{event.event_cycle}",
    ]

    time_diff = get_verbal_time_diff(datetime.now(TZ_TAIPEI), event.next_due_at)
    if time_diff == "今天":
        lines.append(f"🗓️ 下次時間：{event.next_due_at.strftime('%Y-%m-%d')}")
    else:
        lines.append(f"🗓️ 原定時間：{event.next_due_at.strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已延後：{time_diff}")

    bubble = flex_bubble_template(title=title, lines=lines)
    msg = FlexMessage(altText=title, contents=bubble)
    return msg


def shared_event(event: EventData, owner_profile: dict[str, str]) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"The event '{event.event_name}' does not have a valid next due date.")

    title = f"🍞 幫忙提醒一下{owner_profile.get('displayName')}，又該{event.event_name}囉～"
    lines = [
        f"👥 來自{owner_profile.get('displayName')}的共享事件",
        f"🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 重複週期：{event.event_cycle}",
    ]

    time_diff = get_verbal_time_diff(datetime.now(TZ_TAIPEI), event.next_due_at)
    if time_diff == "今天":
        lines.append(f"🗓️ 下次時間：{event.next_due_at.strftime('%Y-%m-%d')}")
    else:
        lines.append(f"🗓️ 原定時間：{event.next_due_at.strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已延後：{time_diff}")

    bubble = flex_bubble_template(title=title, lines=lines)
    msg = FlexMessage(altText=title, contents=bubble)
    return msg
