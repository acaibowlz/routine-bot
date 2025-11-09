from linebot.v3.messaging import ButtonsTemplate, MessageAction, TemplateMessage, TextMessage

from routine_bot.constants import TZ_TAIPEI
from routine_bot.models import EventData


def prompt_for_event_name() -> TextMessage:
    return TextMessage(text="請輸入你要刪除的事項名稱 ✨")


def comfirm_event_deletion(event: EventData) -> TemplateMessage:
    if event.reminder_enabled:
        if event.next_due_at is None:
            raise AttributeError(f"Event '{event.event_name}' is missing its next due date")
        text = (
            f"\n🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}\n\n"
            f"🔔 下次提醒：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}\n\n"
            "🍞 確定要刪除這片吐司嗎？"
        )
    else:
        text = (
            f"\n🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}\n\n🔕 提醒設定：關閉\n\n🍞 確定要刪除這片吐司嗎？"
        )
    template = ButtonsTemplate(
        title=f"👋 刪除［{event.event_name}］",
        text=text,
        actions=[
            MessageAction(label="是", text="刪除吐司"),
            MessageAction(label="否", text="取消刪除"),
        ],
    )
    msg = TemplateMessage(
        altText=f"👋 刪除［{event.event_name}］🍞 確定要刪除這片吐司嗎？",
        template=template,
    )
    return msg


def deleted(event_name: str) -> TextMessage:
    return TextMessage(text=f"✅［{event_name}］已成功刪除！")


def cancelled() -> TextMessage:
    return TextMessage(text="🚫 已取消刪除")


def invalid_delete_confirmation(event: EventData) -> TemplateMessage:
    text = "\n⚠️ 無效的輸入，請再試一次\n\n🍞 確定要刪除這片吐司嗎？"
    template = ButtonsTemplate(
        title=f"👋 刪除［{event.event_name}］",
        text=text,
        actions=[
            MessageAction(label="是", text="刪除吐司"),
            MessageAction(label="否", text="取消刪除"),
        ],
    )
    msg = TemplateMessage(
        altText=f"👋 刪除［{event.event_name}］⚠️ 輸入無效，確定要刪除這片吐司嗎？",
        template=template,
    )
    return msg
