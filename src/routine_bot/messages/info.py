from linebot.v3.messaging import FlexMessage

from routine_bot.constants import FREE_PLAN_MAX_EVENTS
from routine_bot.messages.utils import flex_bubble_template


def event_cycle_example() -> FlexMessage:
    bubble = flex_bubble_template(
        title="🌟 自訂週期輸入格式",
        lines=[
            "支援以下格式：",
            "📌 3 day",
            "📌 2 week",
            "📌 1 month",
            "⚠️ 請直接輸入上述其中一種格式",
        ],
    )
    return FlexMessage(altText="✨ 請輸入循環週期", contents=bubble)


def max_events_reached() -> FlexMessage:
    bubble = flex_bubble_template(
        title="⚠️ 無法新增事項",
        lines=[
            f"🔒 你已達免費方案上限（{FREE_PLAN_MAX_EVENTS} 個事項）",
            "💡 你可以選擇：",
            "🗑️ 刪除一些不再需要的事項",
            "🚀 升級到 Premium 方案，享受無上限新增",
        ],
    )
    msg = FlexMessage(
        altText="⚠️ 無法新增事項，請刪除多餘事項或升級至 Premium",
        contents=bubble,
    )
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


def ongoing_chat_aborted() -> FlexMessage:
    bubble = flex_bubble_template(title="⏸️ 已幫你停下目前的指令", lines=["🍞 可以輸入新的指令，繼續操作囉～"])
    return FlexMessage(altText="🍞 可以輸入新的指令，繼續操作囉～", contents=bubble)
