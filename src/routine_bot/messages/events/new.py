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
    return TextMessage(text="🎯 請輸入欲新增的事件名稱（限 2 至 20 字元）")


def select_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🎯 新事件［{chat_payload['event_name']}］",
        text="\n⬇️ 請選擇事件起始日期",
        actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇事件起始日期", template=template)
    return msg


def enable_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🎯 新事件［{chat_payload['event_name']}］",
        text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⬇️ 請選擇是否設定提醒",
        actions=[
            MessageAction(label="是", text="設定提醒"),
            MessageAction(label="否", text="不設定提醒"),
        ],
    )
    msg = TemplateMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇是否設定提醒", template=template)
    return msg


def select_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🎯 新事件［{chat_payload['event_name']}］",
        text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⬇️ 請選擇事件週期",
        actions=[
            MessageAction(label="1 天", text="1 day"),
            MessageAction(label="1 週", text="1 week"),
            MessageAction(label="1 個月", text="1 month"),
            MessageAction(label="輸入自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇事件週期", template=template)
    return msg


def event_cycle_example() -> FlexMessage:
    bubble = flex_bubble_template(
        title="🌟 自訂週期輸入格式",
        lines=["支援以下格式：", "📌 3 day", "📌 2 week", "📌 1 month", "⚠️ 請直接輸入上述其中一種格式"],
    )
    return FlexMessage(altText="➡️ 輸入自訂週期", contents=bubble)


def event_created_no_reminder(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 新增完成！",
        lines=[
            f"🎯 新事件［{chat_payload['event_name']}］",
            f"🗓 起始日期：{chat_payload['start_date'][:10]}",
            "🔕 提醒設定：關閉",
        ],
    )
    return FlexMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］✅ 新增完成！", contents=bubble)


def event_created_with_reminder(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 新增完成！",
        lines=[
            f"🎯 新事件［{chat_payload['event_name']}］",
            f"🗓 起始日期：{chat_payload['start_date'][:10]}",
            "🔔 提醒設定：開啟",
            f"🔁 事件週期：{chat_payload['event_cycle']}",
        ],
    )
    return FlexMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］✅ 新增完成！", contents=bubble)


def invalid_input_for_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🎯 新事件［{chat_payload['event_name']}］",
        text="\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請透過下方按鈕選擇事件起始日期",
        actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請選擇事件起始日期", template=template
    )
    return msg


def invalid_selection_for_start_date_exceeds_today(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🎯 新事件［{chat_payload['event_name']}］",
        text="\n⚠️ 起始日期不可超過今天\n\n⬇️ 請重新選擇起始日期",
        actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 起始日期不可超過今天，請重新選擇起始日期",
        template=template,
    )
    return msg


def invalid_input_for_enable_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🎯 新事件［{chat_payload['event_name']}］",
        text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請透過下方按鈕是否設定提醒",
        actions=[
            MessageAction(label="是", text="設定提醒"),
            MessageAction(label="否", text="不設定提醒"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🎯 新事件［{chat_payload['event_name']}］ ⚠️ 輸入無效，請重新選擇是否設定提醒", template=template
    )
    return msg


def invalid_input_for_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🎯 新事件［{chat_payload['event_name']}］",
        text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請選擇事件週期",
        actions=[
            MessageAction(label="1 天", text="1 day"),
            MessageAction(label="1 週", text="1 week"),
            MessageAction(label="1 個月", text="1 month"),
            MessageAction(label="輸入自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請重新選擇事件週期", template=template
    )
    return msg
