from linebot.v3.messaging import (
    ButtonsTemplate,
    DatetimePickerAction,
    FlexMessage,
    MessageAction,
    TemplateMessage,
    TextMessage,
)

from routine_bot.messages.utils import flex_bubble_template


def prompt_for_event_name() -> TextMessage:
    return TextMessage(text="請輸入要記的事項名稱（2～10 個字）✨")


def select_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新的吐司［{chat_payload['event_name']}］",
        text="\n🗓 要從哪一天開始紀錄這件事呢？\n\n✨ 請選擇日期",
        actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(altText=f"🗓 請選擇［{chat_payload['event_name']}］的開始日期", template=template)
    return msg


def enable_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新的吐司［{chat_payload['event_name']}］",
        text=f"\n🗓 開始日期：{chat_payload['start_date'][:10]}\n\n💭 要不要幫這個事項設定提醒呢？\n\n✨ 請選擇",
        actions=[
            MessageAction(label="要", text="設定提醒"),
            MessageAction(label="不用", text="不設定提醒"),
        ],
    )
    msg = TemplateMessage(
        altText=f"⏰ 是否為［{chat_payload['event_name']}］設定提醒？",
        template=template,
    )
    return msg


def select_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新的吐司［{chat_payload['event_name']}］",
        text=f"\n🗓 開始日期：{chat_payload['start_date'][:10]}\n\n💭 這個事項應該要多久重複一次呢？\n\n✨ 請選擇週期",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🔁 請選擇［{chat_payload['event_name']}］的重複週期",
        template=template,
    )
    return msg


def event_cycle_example() -> FlexMessage:
    bubble = flex_bubble_template(
        title="🌟 自訂週期輸入格式",
        lines=[
            "支援以下格式：",
            "📌 3 day",
            "📌 2 week",
            "📌 1 month",
            "⚠️ 請直接輸入上述其中一種格式",
        ],
    )
    return FlexMessage(altText="➡️ 輸入自訂週期", contents=bubble)


def event_created_no_reminder(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 吐司已準備就緒",
        lines=[
            f"🍞 名稱：{chat_payload['event_name']}",
            f"🗓 開始日期：{chat_payload['start_date'][:10]}",
            "🔕 提醒狀態：關閉",
        ],
    )
    return FlexMessage(
        altText=f"🍞 新的吐司［{chat_payload['event_name']}］已準備就緒",
        contents=bubble,
    )


def event_created_with_reminder(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 吐司已準備就緒",
        lines=[
            f"🍞 名稱：{chat_payload['event_name']}",
            f"🗓 開始日期：{chat_payload['start_date'][:10]}",
            f"🔁 重複週期：{chat_payload['event_cycle']}",
            "🔔 提醒：已開啟",
        ],
    )
    return FlexMessage(
        altText=f"🍞 新的吐司［{chat_payload['event_name']}］已準備就緒",
        contents=bubble,
    )


def invalid_input_for_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新的吐司［{chat_payload['event_name']}］",
        text="\n⚠️ 嗯～我不太確定你的意思\n\n✨ 幫我用下方按鈕選個開始日期吧",
        actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🍞 吐司［{chat_payload['event_name']}］⚠️ 輸入無效，請重新選擇開始日期",
        template=template,
    )
    return msg


def invalid_selection_for_start_date_exceeds_today(
    chat_payload: dict[str, str],
) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新的吐司［{chat_payload['event_name']}］",
        text="\n⚠️ 開始日期不能比今天晚喔\n\n✨ 幫我重新選個日期吧",
        actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🍞 吐司［{chat_payload['event_name']}］⚠️ 開始日期不能比今天晚，請重新選擇日期",
        template=template,
    )
    return msg


def invalid_input_for_enable_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新的吐司［{chat_payload['event_name']}］",
        text="\n🗓 ⚠️ 嗯～我不太確定你的意思\n\n✨ 再幫我選一次，要不要開啟提醒呢？",
        actions=[
            MessageAction(label="要", text="設定提醒"),
            MessageAction(label="不用", text="不設定提醒"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 吐司［{chat_payload['event_name']}］⚠️ 輸入無效，請重新選擇是否開啟提醒",
        template=template,
    )
    return msg


def invalid_input_for_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 新的吐司［{chat_payload['event_name']}］",
        text="\n⚠️ 嗯～我不太確定你的意思\n\n✨ 幫我透過下方按鈕選擇重複週期吧",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請重新選擇事件週期",
        template=template,
    )
    return msg
