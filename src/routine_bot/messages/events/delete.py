from linebot.v3.messaging import (
    ButtonsTemplate,
    MessageAction,
    TemplateMessage,
    TextMessage,
)

from routine_bot.models import EventData


def prompt_for_event_name() -> TextMessage:
    return TextMessage(text="🎯 請輸入欲刪除的事件名稱")


def comfirm_event_deletion(event: EventData) -> TemplateMessage:
    if event.reminder_enabled:
        text = (
            "\n"
            f"✅ 最近完成：{event.last_done_at.strftime('%Y-%m-%d')}\n\n"
            "🔔 提醒設定：開啟\n\n"
            f"🔁 事件週期：{event.event_cycle}\n\n"
            "⬇️ 確定要刪除這個事件嗎？"
        )
    else:
        text = (
            f"\n✅ 最近完成：{event.last_done_at.strftime('%Y-%m-%d')}\n\n🔕 提醒設定：關閉\n\n⬇️ 確定要刪除這個事件嗎？"
        )
    template = ButtonsTemplate(
        title=f"🗑️ 刪除［{event.event_name}］",
        text=text,
        actions=[
            MessageAction(label="是", text="刪除事件"),
            MessageAction(label="否", text="取消刪除"),
        ],
    )
    msg = TemplateMessage(altText=f"🗑️ 刪除［{event.event_name}］➡️ 確定要刪除這個事件嗎？", template=template)
    return msg


def deleted(event_name: str) -> TextMessage:
    return TextMessage(text=f"🗑️ 事件［{event_name}］已成功刪除！")


def cancelled(event_name: str) -> TextMessage:
    return TextMessage(text=f"🚫 已取消刪除事件［{event_name}］")


def invalid_delete_confirmation(event: EventData) -> TemplateMessage:
    if event.reminder_enabled:
        text = (
            "\n"
            "⚠️ 無效的輸入，請再試一次\n\n"
            f"✅ 最近完成：{event.last_done_at.strftime('%Y-%m-%d')}\n\n"
            "🔔 提醒設定：開啟\n\n"
            f"🔁 事件週期：{event.event_cycle}\n\n"
            "⬇️ 確定要刪除這個事件嗎？"
        )
    else:
        text = (
            "\n"
            "⚠️ 無效的輸入，請再試一次\n\n"
            f"✅ 最近完成：{event.last_done_at.strftime('%Y-%m-%d')}\n\n"
            "🔕 提醒設定：關閉\n\n"
            f"⬇️ 確定要刪除這個事件嗎？"
        )
    template = ButtonsTemplate(
        title=f"🗑️ 刪除［{event.event_name}］",
        text=text,
        actions=[
            MessageAction(label="是", text="刪除事件"),
            MessageAction(label="否", text="取消刪除"),
        ],
    )
    msg = TemplateMessage(altText=f"🗑️ 刪除［{event.event_name}］⚠️ 輸入無效，確定要刪除這個事件嗎？", template=template)
    return msg
