from linebot.v3.messaging import FlexMessage

from routine_bot.messages.utils import flex_bubble_template


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(title="🍞 取消分享事項", lines=["📝 請輸入要取消分享的事項名稱"])
    return FlexMessage(altText="🍞 請輸入要取消分享的事項名稱", contents=bubble)
