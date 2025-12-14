from linebot.v3.messaging import (
    ButtonsTemplate,
    DatetimePickerAction,
    FlexMessage,
    TemplateMessage,
)

from routine_bot.messages.utils import flex_bubble_template


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(title="🍞 新增完成紀錄", lines=["📝 請輸入要新增完成紀錄的事項名稱"])
    return FlexMessage(altText="🍞 請輸入要新增完成紀錄的事項名稱", contents=bubble)


def select_done_at(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 更新［{chat_payload['event_name']}］的完成日期",
        text="\n🗓 最近是哪一天完成的呢？\n\n✨ 幫我用下方按鈕選個日期吧",
        actions=[DatetimePickerAction(label="選擇完成日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(altText=f"🗓 請選擇［{chat_payload['event_name']}］完成時間", template=template)
    return msg


def succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 已幫你記下完成日期囉～",
        lines=[f"🍞 事項：{chat_payload['event_name']}", f"🗓 完成日期：{chat_payload['done_at'][:10]}"],
    )
    msg = FlexMessage(altText=f"✅［{chat_payload['event_name']}］已新增完成紀錄", contents=bubble)
    return msg


def invalid_input_for_done_at(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 更新［{chat_payload['event_name']}］的完成日期",
        text="\n⚠️ 嗯？我不太確定你的意思\n\n✨ 幫我用下方按鈕選個日期吧",
        actions=[DatetimePickerAction(label="選擇完成日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🍞 更新［{chat_payload['event_name']}］完成紀錄 ⚠️ 輸入無效，請重新選擇完成日期", template=template
    )
    return msg


def invalid_done_date_selected_exceeds_today(
    chat_payload: dict[str, str],
) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 更新［{chat_payload['event_name']}］的完成日期",
        text="\n⚠️ 完成日期不能比今天晚喔\n\n✨ 幫我重新選個日期吧",
        actions=[DatetimePickerAction(label="選擇完成日期", data=chat_payload["chat_id"], mode="date")],
    )
    msg = TemplateMessage(
        altText=f"🍞 新事項［{chat_payload['event_name']}］⚠️ 開始日期不能比今天晚，請重新選擇", template=template
    )
    return msg
