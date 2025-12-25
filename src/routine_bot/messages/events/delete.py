from linebot.v3.messaging import ButtonsTemplate, FlexMessage, MessageAction, TemplateMessage

from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.options import ConfirmDeletionOptions
from routine_bot.messages.utils import flex_bubble_template
from routine_bot.models import EventData


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(title="🍞 刪除事項", lines=["📝 請輸入要刪除的事項名稱"])
    return FlexMessage(altText="🍞 請輸入要刪除的事項名稱", contents=bubble)


def comfirm_event_deletion(event: EventData) -> TemplateMessage:
    if event.reminder_enabled:
        if event.next_due_at is None:
            raise AttributeError(f"Event does not have a valid next due date: {event.event_id}")

        text = (
            f"\n🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}\n\n"
            f"🔔 下次提醒：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}\n\n"
            "✨ 確定要刪除這個事項嗎？"
        )
    else:
        text = (
            f"\n🗓 上次是：{event.last_done_at.strftime('%Y-%m-%d')}\n\n🔕 提醒設定：關閉\n\n✨ 確定要刪除這個事項嗎？"
        )
    template = ButtonsTemplate(
        title=f"🍞 刪除［{event.event_name}］",
        text=text,
        actions=[
            MessageAction(label="是", text=ConfirmDeletionOptions.DELETE.value),
            MessageAction(label="否", text=ConfirmDeletionOptions.CANCEL.value),
        ],
    )
    msg = TemplateMessage(altText=f"🍞 確定要刪除［{event.event_name}］嗎？", template=template)
    return msg


def succeeded(event_name: str) -> FlexMessage:
    bubble = flex_bubble_template(title=f"🍞 刪除［{event_name}］", lines=["✅ 已成功刪除！"])
    return FlexMessage(altText=f"✅［{event_name}］已成功刪除！", contents=bubble)


def cancelled(event_name: str) -> FlexMessage:
    bubble = flex_bubble_template(title=f"🍞 刪除［{event_name}］", lines=["🚫 已取消刪除"])
    return FlexMessage(altText="🚫 已取消刪除", contents=bubble)


def invalid_delete_confirmation(event: EventData) -> TemplateMessage:
    text = "\n⚠️ 嗯？我不太確定你的意思\n\n✨ 請幫我從下方按鈕確認是否刪除"
    template = ButtonsTemplate(
        title=f"🍞 刪除［{event.event_name}］",
        text=text,
        actions=[
            MessageAction(label="是", text="刪除事項"),
            MessageAction(label="否", text="取消刪除"),
        ],
    )
    msg = TemplateMessage(altText=f"⚠️ 輸入無效，確定要刪除［{event.event_name}］嗎？", template=template)
    return msg
