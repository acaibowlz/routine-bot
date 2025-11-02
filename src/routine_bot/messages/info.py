from linebot.v3.messaging import FlexMessage, TextMessage

from routine_bot.constants import FREE_PLAN_MAX_EVENTS
from routine_bot.messages.utils import flex_bubble_template


def unrecognized_command() -> TextMessage:
    return TextMessage(text="指令無法辨識🤣 請再試一次😌")


def event_name_duplicated(event_name: str) -> TextMessage:
    return TextMessage(text=f"已有叫做［{event_name}］的事件🤣 請換個名稱再試一次😌")


def event_name_not_found(event_name: str) -> TextMessage:
    return TextMessage(text=f"找不到叫做［{event_name}］的事件😱 請再試一次😌")


def event_name_too_long() -> TextMessage:
    return TextMessage(text="事件名稱不可以超過 20 字元🤣 請再試一次😌")


def event_name_too_short() -> TextMessage:
    return TextMessage(text="事件名稱不可以少於 2 字元🤣 請再試一次😌")


def max_events_reached() -> FlexMessage:
    bubble = flex_bubble_template(
        title="⚠️ 無法新增事件",
        lines=[
            f"🔒 你已超過免費方案的 {FREE_PLAN_MAX_EVENTS} 個事件上限",
            "💡 你可以選擇：",
            "🗑️ 刪除超量事件，繼續使用免費方案",
            "🚀 升級至 premium，享受新增無上限",
        ],
    )
    msg = FlexMessage(altText="⚠️ 無法新增事件，請刪除超量事件或升級至 premium", contents=bubble)
    return msg


def no_ongoing_chat() -> TextMessage:
    return TextMessage(text="沒有進行中的操作可以取消🤣")


def ongoing_chat_aborted() -> TextMessage:
    return TextMessage(text="已中止目前的操作🙏\n請重新輸入新的指令😉")
