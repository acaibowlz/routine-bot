import base64

from linebot.v3.messaging import (
    ButtonsTemplate,
    ClipboardAction,
    FlexMessage,
    TemplateMessage,
)

from routine_bot.enums.command import Command
from routine_bot.messages.utils import flex_bubble_template


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(title="🍞 分享事項", lines=["📝 請輸入要分享的事項名稱"])
    return FlexMessage(altText="🍞 請輸入要分享的事項名稱", contents=bubble)


def _create_share_code(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).rstrip(b"=").decode()


def show_recipient_instruction(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 分享［{chat_payload['event_name']}］",
        text=(
            "\n✉ 請接收方依照以下步驟操作：\n\n"
            f"1️⃣ 輸入 {Command.RECEIVE.value}\n\n"
            "2️⃣ 貼上分享碼\n\n"
            "✨ 就能把這個事項同步給對方囉～"
        ),
        actions=[ClipboardAction(label="📋 複製分享碼", clipboardText=_create_share_code(chat_payload["event_id"]))],
    )
    return TemplateMessage(altText=f"🍞 分享［{chat_payload['event_name']}］", template=template)


def reached_max_share_count(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title=f"🍞 分享［{chat_payload['event_name']}］",
        lines=["⚠️ 目前這個事項已達分享上限囉", "💭 要不要先整理一下目前的分享對象呢"],
    )
    msg = FlexMessage(
        altText=f"⚠️ 目前事項［{chat_payload['event_name']}］已達分享上限",
        contents=bubble,
    )
    return msg


def invalid_event_must_enable_reminder(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title=f"🍞 分享［{chat_payload['event_name']}］",
        lines=["🔕 這個事項沒有設定提醒", "⚠️ 將提醒打開後，就能順利分享囉！"],
    )
    return FlexMessage(altText=f"🍞 分享［{chat_payload['event_name']}］需要先開啟提醒", contents=bubble)
