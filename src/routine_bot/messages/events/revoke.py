import ast

from linebot.v3.messaging import ButtonsTemplate, FlexMessage, MessageAction, TemplateMessage

from routine_bot.messages.utils import flex_bubble_template


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(title="🍞 取消分享事項", lines=["📝 請輸入要取消分享的事項名稱"])
    return FlexMessage(altText="📝 請輸入要取消分享的事項名稱", contents=bubble)


def no_recipient(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title=f"🍞 取消分享［{chat_payload['event_name']}］", lines=["⚠️ 目前這個事項沒有設定任何分享對象～"]
    )
    return FlexMessage(altText=f"⚠️ 目前事項［{chat_payload['event_name']}］沒有設定任何分享對象", contents=bubble)


def select_recipient(chat_payload: dict[str, str]) -> TemplateMessage:
    recipient_info = ast.literal_eval(chat_payload["recipient_info"])
    buttons = [MessageAction(label=f"{name}", text=f"{name}") for name in recipient_info.keys()]
    template = ButtonsTemplate(
        title=f"🍞 取消分享［{chat_payload['event_name']}］",
        text="\n💭 目前事項的分享對象如下\n\n✨ 請選擇你想要取消分享權限的對象～",
        actions=buttons,
    )
    msg = TemplateMessage(altText="💭 請選擇想要取消分享權限的對象", template=template)
    return msg


def recipient_not_found(chat_payload: dict[str, str]) -> TemplateMessage:
    recipient_info = ast.literal_eval(chat_payload["recipient_info"])
    buttons = [MessageAction(label=f"{name}", text=f"{name}") for name in recipient_info.keys()]
    template = ButtonsTemplate(
        title=f"🍞 取消分享［{chat_payload['event_name']}］",
        text="\n⚠️ 嗯？你提供的使用者似乎不在目前的分享對象中\n\n✨ 請從下方按鈕選擇你想要取消分享權限的對象～",
        actions=buttons,
    )
    msg = TemplateMessage(altText="💭 請選擇想要取消分享權限的對象", template=template)
    return msg


def recipient_revoked(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title=f"✅ 成功取消了{chat_payload['selected_recipient']}的共享權限",
        lines=[f"🍞 已取消了{chat_payload['selected_recipient']}對［{chat_payload['event_name']}］的共享權限"],
    )
    return FlexMessage(altText=f"✅ 成功取消了{chat_payload['selected_recipient']}的共享權限", contents=bubble)
