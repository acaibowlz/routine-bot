from linebot.v3.messaging import ButtonsTemplate, FlexMessage, MessageAction, TemplateMessage, TextMessage

from routine_bot.enums.options import EditEventOptions, ToggleReminderOptions
from routine_bot.messages.utils import flex_bubble_template


def enter_event_name() -> TextMessage:
    return TextMessage(text="請輸入欲編輯的事項名稱 🍞")


def select_option(chat_payload: dict[str, str]) -> TemplateMessage:
    actions = [
        MessageAction(label="編輯名稱", text=f"{EditEventOptions.NAME.value}"),
        MessageAction(label="編輯提醒設定", text=f"{EditEventOptions.REMINDER.value}"),
    ]
    if chat_payload["reminder_enabled"] == "True":
        actions.append(MessageAction(label="編輯重複週期", text=f"{EditEventOptions.EVENT_CYCLE.value}"))
    template = ButtonsTemplate(
        title=f"🍞 編輯［{chat_payload['event_name']}］",
        text="\n📝 想調整哪個部分呢？\n\n✨ 從下方選一個來修改吧～",
        actions=actions,
    )
    msg = TemplateMessage(altText=f"🍞 編輯［{chat_payload['event_name']}］➡️ 請選擇想調整的項目", template=template)
    return msg


def enter_new_event_name(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title=f"🍞 重新命名［{chat_payload['event_name']}］", lines=["✨ 請輸入新的事項名稱（2～10 個字）"]
    )
    msg = FlexMessage(altText=f"🍞 重新命名［{chat_payload['event_name']}］", contents=bubble)
    return msg


def toggle_reminder(chat_payload: dict[str, str]):
    if chat_payload["reminder_enabled"] == "True":
        text = "\n🔔 目前的提醒是開啟的喔～\n\n✨ 想要先關閉一下嗎？"
    else:
        text = "\n🔕 目前的提醒是關閉的喔～\n\n✨ 要不要幫你開啟提醒呢？"

    template = ButtonsTemplate(
        title=f"🍞 調整［{chat_payload['event_name']}］的提醒",
        text=text,
        actions=[
            MessageAction(label="是，修改設定", text=ToggleReminderOptions.CONFIRM.value),
            MessageAction(label="不用，維持現狀", text=ToggleReminderOptions.CANCEL.value),
        ],
    )

    msg = TemplateMessage(
        altText=f"🍞 調整［{chat_payload['event_name']}］的提醒",
        template=template,
    )
    return msg


def enter_new_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 調整［{chat_payload['event_name']}］的重複週期",
        text=f"\n🗓 目前週期：{chat_payload['event_cycle']}\n\n✨ 請選擇新的週期",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(altText=f"🍞 調整［{chat_payload['event_name']}］的重複週期", template=template)
    return msg


def edit_event_name_succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="🍞 編輯成功",
        lines=[f"✅ 已幫你將［{chat_payload['event_name']}］重新命名為［{chat_payload['new_event_name']}］～"],
    )
    msg = FlexMessage(
        altText=f"🍞 已將［{chat_payload['event_name']}］重新命名為［{chat_payload['new_event_name']}］",
        contents=bubble,
    )
    return msg


def toggle_reminder_cancelled(chat_payload: dict[str, str]) -> FlexMessage:
    if chat_payload["reminder_enabled"] == "True":
        lines = [f"🔔［{chat_payload['event_name']}］的提醒將維持目前的開啟狀態～"]
    else:
        lines = [f"🔕［{chat_payload['event_name']}］的提醒將維持目前的關閉狀態～"]
    bubble = flex_bubble_template(title="🚫 已取消這次的修改", lines=lines)
    msg = FlexMessage(altText="🚫 已取消這次的修改", contents=bubble)
    return msg


def toggle_reminder_succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    if chat_payload["reminder_enabled"] == "True":
        lines = [f"🔕 已幫你關閉［{chat_payload['event_name']}］的提醒囉～"]
        bubble = flex_bubble_template(title="🍞 編輯成功", lines=lines)
        msg = FlexMessage(altText=f"🍞 已關閉［{chat_payload['event_name']}］的提醒囉", contents=bubble)
        return msg
    else:
        if chat_payload.get("new_event_cycle"):
            lines = [
                f"✅ 已幫你開啟［{chat_payload['event_name']}］的提醒囉～",
                f"🔔 下次提醒：{chat_payload['next_due_at'][:10]}",
                f"🔁 重複週期：{chat_payload['new_event_cycle']}",
            ]
        else:
            lines = [
                f"✅ 已幫你開啟［{chat_payload['event_name']}］的提醒囉～",
                f"🔔 下次提醒：{chat_payload['next_due_at'][:10]}",
                f"🔁 重複週期：{chat_payload['event_cycle']}",
            ]
        bubble = flex_bubble_template(title="🍞 編輯成功", lines=lines)
        msg = FlexMessage(altText=f"🍞 已開啟［{chat_payload['event_name']}］的提醒囉", contents=bubble)
        return msg


def proceed_to_set_event_cycle(chat_payload: dict[str, str]):
    template = ButtonsTemplate(
        title="🍞 請接著設定重複週期",
        text=f"\n🔁 尚未設定［{chat_payload['event_name']}］的重複週期\n\n✨ 請由下方選擇重複週期",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(altText="🍞 請接著設定重複週期", template=template)
    return msg


def edit_event_cycle_succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="🍞 編輯成功",
        lines=[
            f"✅ 已幫你更新［{chat_payload['event_name']}］的重複週期～",
            f"🗓 上次是：{chat_payload['last_done_at'][:10]}",
            f"🔁 新的重複週期：{chat_payload['event_cycle']}",
            f"🔔 下次提醒：{chat_payload['next_due_at'][:10]}",
        ],
    )
    msg = FlexMessage(altText=f"🍞 已更新［{chat_payload['event_name']}］的重複週期囉", contents=bubble)
    return msg


def invalid_edit_option_entry(chat_payload: dict[str, str]):
    actions = [
        MessageAction(label="編輯名稱", text=f"{EditEventOptions.NAME.value}"),
        MessageAction(label="編輯提醒設定", text=f"{EditEventOptions.REMINDER.value}"),
    ]
    if chat_payload["reminder_enabled"] == "True":
        actions.append(MessageAction(label="編輯重複週期", text=f"{EditEventOptions.EVENT_CYCLE.value}"))
    template = ButtonsTemplate(
        title=f"🍞 編輯［{chat_payload['event_name']}］",
        text="\n⚠️ 嗯～我不太確定你的意思\n\n✨ 幫我從下方選擇一個項目吧～",
        actions=actions,
    )
    msg = TemplateMessage(
        altText=f"🍞 編輯［{chat_payload['event_name']}］⚠️ 輸入無效，請選擇想調整的項目", template=template
    )
    return msg


def event_cycle_requires_reminder_enabled(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 編輯［{chat_payload['event_name']}］",
        text="\n⚠️ 要先開啟提醒，才可編輯重複週期\n\n✨ 幫我重新選擇想調整的項目吧",
        actions=[
            MessageAction(label="編輯名稱", text=f"{EditEventOptions.NAME.value}"),
            MessageAction(label="編輯提醒設定", text=f"{EditEventOptions.REMINDER.value}"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 編輯［{chat_payload['event_name']}］⚠️ 需要先開啟提醒，才可編輯重複週期", template=template
    )
    return msg


def invalid_toggle_reminder_entry(chat_payload: dict[str, str]):
    if chat_payload["reminder_enabled"] == "True":
        text = "\n⚠️ 嗯～我不太確定你的意思\n\n🔔 目前的提醒是開啟的喔～\n\n✨ 想要先關閉一下嗎？"
    else:
        text = "\n⚠️ 嗯～我不太確定你的意思\n\n🔕 目前的提醒是關閉的喔～\n\n✨ 要不要幫你開啟提醒呢？"
    template = ButtonsTemplate(
        title=f"🍞 調整［{chat_payload['event_name']}］的提醒",
        text=text,
        actions=[
            MessageAction(label="是，修改設定", text=ToggleReminderOptions.CONFIRM.value),
            MessageAction(label="不用，維持現狀", text=ToggleReminderOptions.CANCEL.value),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 調整［{chat_payload['event_name']}］的提醒 ⚠️ 輸入無效，請重新選擇是否修改設定",
        template=template,
    )
    return msg


def invalid_event_cycle_entry(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 調整［{chat_payload['event_name']}］的重複週期",
        text="\n⚠️ 嗯～我不太確定你的意思\n\n✨ 請由下方選擇重複週期",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 調整［{chat_payload['event_name']}］的重複週期 ⚠️ 輸入無效，請重新選擇週期",
        template=template,
    )
    return msg
