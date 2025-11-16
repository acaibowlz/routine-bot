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
        text = "\n🔔 目前的提醒設定：開啟\n\n✨ 要關閉提醒嗎～"
    else:
        text = "\n🔕 目前的提醒設定：關閉\n\n✨ 要開啟提醒嗎～"
    template = ButtonsTemplate(
        title=f"🍞 編輯［{chat_payload['event_name']}］的提醒",
        text=text,
        actions=[
            MessageAction(label="是，修改設定", text=ToggleReminderOptions.CONFIRM.value),
            MessageAction(label="否，保留目前設定", text=ToggleReminderOptions.CANCEL.value),
        ],
    )
    msg = TemplateMessage(altText=f"🍞 編輯［{chat_payload['event_name']}］的提醒設定", template=template)
    return msg


def enter_new_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 編輯［{chat_payload['event_name']}］的重複週期",
        text=f"\n🗓 目前週期：{chat_payload['event_cycle']}\n\n✨ 請選擇新的週期",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(altText=f"🍞 編輯［{chat_payload['event_name']}］的重複週期", template=template)
    return msg


def edit_event_name_succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(title="✅ 編輯成功", lines=[f"🍞 新名稱：{chat_payload['new_event_name']}"])
    msg = FlexMessage(altText="✅ 編輯成功", contents=bubble)
    return msg


def toggle_reminder_cancelled(chat_payload: dict[str, str]) -> FlexMessage:
    if chat_payload["reminder_enabled"] == "True":
        lines = ["🔔 將維持目前開啟提醒的狀態"]
    else:
        lines = ["🔕 將維持目前關閉提醒的狀態"]
    bubble = flex_bubble_template(title="🚫 已取消編輯", lines=lines)
    msg = FlexMessage(altText="🚫 已取消編輯", contents=bubble)
    return msg


def toggle_reminder_succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    if chat_payload["reminder_enabled"] == "True":
        lines = ["🔕 已將提醒關閉～"]
    else:
        lines = ["🔔 已將提醒開啟～"]
    bubble = flex_bubble_template(title="✅ 編輯成功", lines=lines)
    msg = FlexMessage(altText="✅ 編輯成功", contents=bubble)
    return msg


def toggle_reminder_succeeded_event_cycle_required(chat_payload: dict[str, str]):
    template = ButtonsTemplate(
        title="🔔 已將提醒開啟 🔁 請接著繼續設定重複週期",
        text=f"\n🗓 尚未設定［{chat_payload['event_name']}］的重複週期\n\n✨ 請由下方選擇重複週期",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(altText="🔔 已將提醒開啟 🔁 請接著繼續設定重複週期", template=template)
    return msg


def edit_event_cycle_succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title="✅ 編輯成功",
        lines=[
            f"🍞 新的重複週期：{chat_payload['new_event_cycle']}",
            f"🗓 上次是：{chat_payload['last_done_at'][:10]}",
            f"🔔 下次提醒：{chat_payload['next_due_at'][:10]}",
        ],
    )
    msg = FlexMessage(altText="✅ 編輯成功", contents=bubble)
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
        text="\n⚠️ 需要先開啟提醒，才可編輯重複週期～\n\n✨ 幫我重新選擇想調整的項目吧",
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
        text = "\n⚠️ 嗯～我不太確定你的意思\n\n🔔 目前的提醒設定：開啟\n\n✨ 要關閉提醒嗎～"
    else:
        text = "\n⚠️ 嗯～我不太確定你的意思\n\n🔕 目前的提醒設定：關閉\n\n✨ 要開啟提醒嗎～"
    template = ButtonsTemplate(
        title=f"🍞 編輯［{chat_payload['event_name']}］的提醒",
        text=text,
        actions=[
            MessageAction(label="是，修改設定", text=ToggleReminderOptions.CONFIRM.value),
            MessageAction(label="否，保留目前設定", text=ToggleReminderOptions.CANCEL.value),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 編輯［{chat_payload['event_name']}］的提醒設定 ⚠️ 輸入無效，請重新選擇是否修改設定",
        template=template,
    )
    return msg


def invalid_event_cycle_entry(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title=f"🍞 編輯［{chat_payload['event_name']}］",
        text="\n⚠️ 嗯～我不太確定你的意思\n\n✨ 幫我從下方選擇新的重複週期吧",
        actions=[
            MessageAction(label="每天", text="1 day"),
            MessageAction(label="每週一次", text="1 week"),
            MessageAction(label="每月一次", text="1 month"),
            MessageAction(label="自訂週期（點我看範例）", text="example"),
        ],
    )
    msg = TemplateMessage(
        altText=f"🍞 編輯［{chat_payload['event_name']}］的提醒週期 ⚠️ 輸入無效，請重新選擇新的重複週期",
        template=template,
    )
    return msg
