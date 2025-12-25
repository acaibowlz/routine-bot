from datetime import datetime

from linebot.v3.messaging import FlexMessage

from routine_bot.constants import FREE_PLAN_MAX_EVENTS, TZ_TAIPEI
from routine_bot.messages.utils import flex_bubble_template, get_verbal_time_diff
from routine_bot.models import EventData


def user_owned_event(event: EventData) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"Event does not have a valid next due date: {event.event_id}")

    title = f"🍞 又該{event.event_name}囉～"
    lines = [
        f"🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 重複週期：{event.event_cycle}",
    ]

    time_diff = get_verbal_time_diff(datetime.now(), event.next_due_at)
    if time_diff != "今天":
        lines.append(f"🔔 原定時間：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已延後：{time_diff}")

    bubble = flex_bubble_template(title=title, lines=lines)
    msg = FlexMessage(altText=title, contents=bubble)
    return msg


def shared_event(event: EventData, owner_name: str) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"Event does not have a valid next due date: {event.event_id}")

    title = f"🍞 提醒一下{owner_name}，又該{event.event_name}囉～"
    lines = [
        f"👥 來自{owner_name}的共享提醒",
        f"🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}",
        f"🔁 重複週期：{event.event_cycle}",
    ]

    time_diff = get_verbal_time_diff(datetime.now(), event.next_due_at)
    if time_diff != "今天":
        lines.append(f"🔔 原定時間：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}")
        lines.append(f"⏳ 已延後：{time_diff}")

    bubble = flex_bubble_template(title=title, lines=lines)
    msg = FlexMessage(altText=title, contents=bubble)
    return msg


def reminder_disabled() -> FlexMessage:
    bubble = flex_bubble_template(
        title="🔕 提醒功能已停用",
        lines=[
            f"🔒 你已超過免費方案的 {FREE_PLAN_MAX_EVENTS} 個事項上限",
            "💡 你可以選擇：",
            "🗑️ 刪除一些不需要的事項，以恢復提醒功能",
            "🚀 升級至 Premium，享受無上限提醒",
        ],
    )
    msg = FlexMessage(
        altText="🔕 提醒功能已停用，請刪除多餘事項或升級至 Premium",
        contents=bubble,
    )
    return msg
