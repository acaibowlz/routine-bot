from linebot.v3.messaging import (
    ButtonsTemplate,
    DatetimePickerAction,
    FlexMessage,
    MessageAction,
    TemplateMessage,
)

from routine_bot.constants import FREE_PLAN_MAX_EVENTS
from routine_bot.enums.options import NewEventReminderOptions
from routine_bot.messages.utils import flex_bubble_template


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(title="🍞 新事項", lines=["📝 請輸入要記的事項名稱（2～10 個字）"])
    return FlexMessage(altText="📝 請輸入新事項的名稱", contents=bubble)


def select_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新事項［{chat_payload['event_name']}］",
        text="\n💭 要從哪一天開始紀錄這件事呢？\n\n✨ 請選擇開始日期",
        actions=[DatetimePickerAction(label="選擇開始日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(altText=f"🗓 請選擇［{chat_payload['event_name']}］的開始日期", template=template)
    return msg


def enable_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新事項［{chat_payload['event_name']}］",
        text=f"\n🗓 開始日期：{chat_payload['start_date'][:10]}\n\n💭 要不要幫這個事項設定提醒呢？\n\n✨ 請選擇",
        actions=[
            MessageAction(label="要", text=NewEventReminderOptions.ENABLE.value),
            MessageAction(label="不用", text=NewEventReminderOptions.DISABLE.value),
        ],
    )
    msg = TemplateMessage(altText=f"⏰ 是否為［{chat_payload['event_name']}］設定提醒？", template=template)
    return msg


def select_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新事項［{chat_payload['event_name']}］",
        text=f"\n🗓 開始日期：{chat_payload['start_date'][:10]}\n\n💭 這個事項應該要多久重複一次呢？\n\n✨ 請選擇週期",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(altText=f"🔁 請選擇［{chat_payload['event_name']}］的重複週期", template=template)
    return msg


def succeeded_no_reminder(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 新事項已準備就緒",
        lines=[
            f"🍞 名稱：{chat_payload['event_name']}",
            f"🗓 開始日期：{chat_payload['start_date'][:10]}",
            "🔕 提醒狀態：關閉",
        ],
    )
    return FlexMessage(altText=f"🍞 新事項［{chat_payload['event_name']}］已準備就緒", contents=bubble)


def succeeded_with_reminder(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 新事項已準備就緒",
        lines=[
            f"🍞 名稱：{chat_payload['event_name']}",
            f"🗓 開始日期：{chat_payload['start_date'][:10]}",
            f"🔁 重複週期：{chat_payload['event_cycle']}",
            f"🔔 下次提醒：{chat_payload['next_due_at'][:10]}",
        ],
    )
    return FlexMessage(altText=f"🍞 新事項［{chat_payload['event_name']}］已準備就緒", contents=bubble)


def invalid_text_input(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新事項［{chat_payload['event_name']}］",
        text="\n⚠️ 嗯？我不太確定你的意思\n\n✨ 幫我用下方按鈕選個日期吧",
        actions=[DatetimePickerAction(label="選擇開始日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🍞 新事項［{chat_payload['event_name']}］⚠️ 輸入無效，請重新選擇開始日期", template=template
    )
    return msg


def invalid_start_date_selected_exceeds_today(
    chat_payload: dict[str, str],
) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新事項［{chat_payload['event_name']}］",
        text="\n⚠️ 開始日期不能比今天晚喔\n\n✨ 幫我重新選個日期吧",
        actions=[DatetimePickerAction(label="選擇開始日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🍞 新事項［{chat_payload['event_name']}］⚠️ 開始日期不能比今天晚，請重新選擇", template=template
    )
    return msg


def invalid_reminder_option(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新事項［{chat_payload['event_name']}］",
        text="\n🗓 ⚠️ 嗯？我不太確定你的意思\n\n✨ 再幫我選一次，要不要開啟提醒呢？",
        actions=[
            MessageAction(label="要", text=NewEventReminderOptions.ENABLE.value),
            MessageAction(label="不用", text=NewEventReminderOptions.DISABLE.value),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 新事項［{chat_payload['event_name']}］⚠️ 輸入無效，請重新選擇是否開啟提醒", template=template
    )
    return msg


def invalid_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新事項［{chat_payload['event_name']}］",
        text="\n⚠️ 嗯？我不太確定你的意思\n\n✨ 幫我透過下方按鈕選擇重複週期吧",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請重新選擇重複週期", template=template
    )
    return msg


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
