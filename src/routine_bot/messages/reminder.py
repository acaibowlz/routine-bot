from datetime import datetime

from linebot.v3.messaging import FlexMessage

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import flex_bubble_template, get_verbal_time_diff
from routine_bot.models import EventData


def user_owned_event(event: EventData) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"The event '{event.event_name}' does not have a valid next due date.")
    time_diff = get_verbal_time_diff(datetime.now(TZ_TAIPEI), event.next_due_at)

    lines = [
        f"🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 重複週期：{event.event_cycle}",
    ]
    if time_diff == "今天":
        lines.append(f"🗓️ 下次時間：{event.next_due_at.strftime('%Y-%m-%d')}")
        alt_text = f"🍞 溫馨提醒～［{event.event_name}］又到該進行的時間囉 ⏰"
    else:
        lines.append(f"🗓️ 原定時間：{event.next_due_at.strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已延後：{time_diff}")
        alt_text = f"⏰ 溫馨提醒～［{event.event_name}］已延後 {time_diff}"

    bubble = flex_bubble_template(
        title=f"🍞 是時候安排下次的［{event.event_name}］了！",
        lines=lines,
    )
    msg = FlexMessage(altText=alt_text, contents=bubble)
    return msg


def shared_event(event: EventData, owner_profile: dict[str, str]) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"The event '{event.event_name}' does not have a valid next due date.")
    time_diff = get_verbal_time_diff(datetime.now(TZ_TAIPEI), event.next_due_at)

    lines = [
        f"👥 來自共享：{owner_profile.get('displayName')}",
        f"🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 重複週期：{event.event_cycle}",
    ]
    if time_diff == "今天":
        lines.append(f"🗓️ 下次時間：{event.next_due_at.strftime('%Y-%m-%d')}")
        alt_text = f"🍞 溫馨提醒～［{event.event_name}］（來自{owner_profile.get('displayName')}）又到該進行的時間 ⏰"
    else:
        lines.append(f"🗓️ 原定時間：{event.next_due_at.strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已延後：{time_diff}")
        alt_text = f"⏰ 溫馨提醒～［{event.event_name}］（來自{owner_profile.get('displayName')}）已延後 {time_diff}"

    bubble = flex_bubble_template(
        title=f"🍞 是時候安排下次的［{event.event_name}］了！",
        lines=lines,
    )
    msg = FlexMessage(altText=alt_text, contents=bubble)
    return msg
