from linebot.v3.messaging import FlexMessage

from routine_bot.messages.error import error
from routine_bot.messages.utils import flex_bubble_template


def no_ongoing_chat() -> FlexMessage:
    return error(["🍞 沒有正在進行的操作喔"])


def ongoing_chat_aborted() -> FlexMessage:
    bubble = flex_bubble_template(title="⏸️ 已幫你停下目前的指令", lines=["🍞 可以輸入新的指令，繼續操作囉～"])
    return FlexMessage(altText="🍞 可以輸入新的指令，繼續操作囉～", contents=bubble)
