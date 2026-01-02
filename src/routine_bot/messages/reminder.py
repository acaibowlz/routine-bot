
from linebot.v3.messaging import FlexMessage

from routine_bot.constants import FREE_PLAN_MAX_EVENTS
from routine_bot.messages.utils import flex_bubble_template


def user_owned_event(payload: dict[str, str]) -> FlexMessage:
    title = f"🍞 又該{payload['event_name']}囉～"
    lines = [
        f"🗓 上次是：{payload['last_done_at']}",
        f"🔁 重複週期：{payload['event_cycle']}",
    ]
    if payload["time_diff"] != "今天":
        lines.append(f"🔔 原定時間：{payload['time_diff']}")
        lines.append(f"⏳ 已延後：{payload['time_diff']}")

    bubble = flex_bubble_template(title=title, lines=lines)
    msg = FlexMessage(altText=title, contents=bubble)
    return msg


def shared_event(payload: dict[str, str]) -> FlexMessage:
    title = f"🍞 提醒一下{payload['owner_name']}，又該{payload['event_name']}囉～"
    lines = [
        f"👥 來自{payload['owner_name']}的共享提醒",
        f"🗓 上次是：{payload['last_done_at']}",
        f"🔁 重複週期：{payload['event_cycle']}",
    ]
    if payload["time_diff"] != "今天":
        lines.append(f"🔔 原定時間：{payload['time_diff']}")
        lines.append(f"⏳ 已延後：{payload['time_diff']}")

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
