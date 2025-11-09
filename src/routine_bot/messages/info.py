from linebot.v3.messaging import FlexMessage, TextMessage

from routine_bot.constants import FREE_PLAN_MAX_EVENTS
from routine_bot.messages.utils import flex_bubble_template


def unrecognized_command() -> TextMessage:
    return TextMessage(text="嗯～這個指令我不太認識💭\n再試一次看看吧～🍞")


def event_name_duplicated(event_name: str) -> TextMessage:
    return TextMessage(text=f"已經有一片叫做［{event_name}］的吐司囉🍞 再想一個新名字試試吧～😌")


def event_name_not_found(event_name: str) -> TextMessage:
    return TextMessage(text=f"嗯～好像沒有叫做［{event_name}］的吐司喔💭\n再試一次看看吧～🍞")


def event_name_too_long() -> TextMessage:
    return TextMessage(text="嗯～名字好像有點長呢💭（限 10 個字以內喔～）")


def event_name_too_short() -> TextMessage:
    return TextMessage(text="嗯～名字好像有點太短了💭 再加入幾個字吧～🍞")


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


def no_ongoing_chat() -> TextMessage:
    return TextMessage(text="沒有正在進行的操作喔～🍞")


def ongoing_chat_aborted() -> TextMessage:
    return TextMessage(text="已幫你停下目前的操作囉～🍞\n接下來想做什麼呢？\n輸入新的指令試試吧！✨")
