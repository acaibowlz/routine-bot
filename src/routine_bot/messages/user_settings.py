from datetime import datetime, timedelta

from linebot.v3.messaging import (
    ButtonsTemplate,
    DatetimePickerAction,
    FlexMessage,
    MessageAction,
    TemplateMessage,
)

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import flex_bubble_template


def select_option() -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 使用者設定",
        text="\n⬇️ 請選擇以下設定選項",
        actions=[
            MessageAction(label="更改提醒時段", text="更改提醒時段"),
        ],
    )
    msg = TemplateMessage(altText="⚙️ 使用者設定 ➡️ 請選擇設定選項", template=template)
    return msg


def select_new_notification_slot(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 更改提醒時段",
        text=f"\n🕒 當前提醒時段：{chat_payload['current_slot']}\n\n⬇️ 請選擇新的提醒時段",
        actions=[
            DatetimePickerAction(
                label="選擇時段", data=chat_payload["chat_id"], mode="time", initial=chat_payload["current_slot"]
            )
        ],
    )
    msg = TemplateMessage(altText="⚙️ 使用者設定 ➡️ 更改提醒時段", template=template)
    return msg


def notification_slot_updated(chat_payload: dict[str, str]) -> FlexMessage:
    now = datetime.now(TZ_TAIPEI)
    hour = int(chat_payload["new_slot"].split(":")[0])
    time_slot = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if hour <= now.hour:
        next_run = time_slot + timedelta(days=1)
    else:
        next_run = time_slot

    bubble = flex_bubble_template(
        title="✅ 提醒時段已更新",
        lines=[
            f"🕒 新的提醒時段：{chat_payload['new_slot']}",
            "🔄 下一次自動檢查：",
            f"🗓 {next_run.strftime('%Y-%m-%d')} {next_run.strftime('%H:%M')}",
        ],
    )
    msg = FlexMessage(altText="⚙️ 使用者設定 ✅ 提醒時段已更新", contents=bubble)
    return msg


def invalid_input_for_option(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 使用者設定",
        text=f"\n⚠️ 無效的輸入，請再試一次\n\n🕒 當前提醒時段：{chat_payload['current_slot']}\n\n⬇️ 請透過下方按鈕選擇設定選項",
        actions=[
            MessageAction(label="更改提醒時段", text="更改提醒時段"),
        ],
    )
    msg = TemplateMessage(altText="⚙️ 使用者設定 ⚠️ 輸入無效，請再次選擇設定選項", template=template)
    return msg


def invalid_input_for_notification_slot(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 更改提醒時段",
        text=f"\n⚠️ 無效的輸入，請再試一次\n\n🕒 當前提醒時段：{chat_payload['current_slot']}\n\n⬇️ 請透過下方按鈕選擇提醒時段",
        actions=[
            DatetimePickerAction(
                label="選擇時段", data=chat_payload["chat_id"], mode="time", initial=chat_payload["current_slot"]
            )
        ],
    )
    msg = TemplateMessage(altText="⚙️ 更改提醒時段 ⚠️ 輸入無效，請再次選擇提醒時段", template=template)
    return msg


def invalid_notification_slot(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 更改提醒時段",
        text=f"\n⚠️ 無效的輸入，請再試一次\n\n🕒 當前提醒時段：{chat_payload['current_slot']}\n\n⬇️ 請將分鐘部分調整為 0",
        actions=[
            DatetimePickerAction(
                label="選擇時段", data=chat_payload["chat_id"], mode="time", initial=chat_payload["current_slot"]
            )
        ],
    )
    msg = TemplateMessage(altText="⚙️ 更改提醒時段 ⚠️ 輸入無效，請再次選擇提醒時段", template=template)
    return msg
