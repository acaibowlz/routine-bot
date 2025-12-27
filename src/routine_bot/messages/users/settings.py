from datetime import datetime, timedelta

from linebot.v3.messaging import ButtonsTemplate, DatetimePickerAction, FlexMessage, MessageAction, TemplateMessage

from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.options import UserSettingsOptions
from routine_bot.messages.utils import flex_bubble_template


def select_option() -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 使用者設定",
        text="\n🍞 想調整什麼設定呢？\n\n✨ 幫我選一個吧",
        actions=[
            MessageAction(label="更改提醒時段", text=f"{UserSettingsOptions.TIME_SLOT.value}"),
        ],
    )
    msg = TemplateMessage(altText="⚙️ 使用者設定 ➡️ 請選擇想調整的項目", template=template)
    return msg


def select_new_time_slot(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 更改提醒時段",
        text=(
            f"\n🕒 目前的提醒時間是［{chat_payload['current_slot']}］\n\n🍞 想換個時間嗎？\n\n✨ 幫我選個新的提醒時段吧"
        ),
        actions=[
            DatetimePickerAction(
                label="選擇新時段",
                data=chat_payload["chat_id"],
                mode="time",
                initial=chat_payload["current_slot"],
            )
        ],
    )
    msg = TemplateMessage(
        altText=f"⚙️ 更改提醒時段 ➡️ 目前時間：{chat_payload['current_slot']}，請選擇新時段", template=template
    )
    return msg


def succeeded(chat_payload: dict[str, str]) -> FlexMessage:
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
            f"🕒 新的提醒時間是［{chat_payload['new_slot']}］",
            "🔄 下一次自動檢查：",
            f"🗓 {next_run.strftime('%Y-%m-%d')} {next_run.strftime('%H:%M')}",
        ],
    )
    msg = FlexMessage(altText="⚙️ 使用者設定 ✅ 提醒時段已更新", contents=bubble)
    return msg


def invalid_option(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 使用者設定",
        text="\n⚠️ 嗯？我不太確定你的意思\n\n✨ 幫我從下面選一個設定項目吧",
        actions=[
            MessageAction(label="更改提醒時段", text="更改提醒時段"),
        ],
    )
    msg = TemplateMessage(altText="⚙️ 使用者設定 ⚠️ 輸入無效，請重新選擇設定選項", template=template)
    return msg


def invalid_text_input(
    chat_payload: dict[str, str],
) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 更改提醒時段",
        text="\n⚠️ 嗯？我不太確定你的意思\n\n✨ 幫我選個新的提醒時段吧",
        actions=[
            DatetimePickerAction(
                label="選擇新時段",
                data=chat_payload["chat_id"],
                mode="time",
                initial=chat_payload["current_slot"],
            )
        ],
    )
    msg = TemplateMessage(altText="⚙️ 更改提醒時段 ⚠️ 輸入無效，請重新選擇提醒時段", template=template)
    return msg


def invalid_time_slot(chat_payload: dict[str, str]) -> TemplateMessage:
    template = ButtonsTemplate(
        title="⚙️ 更改提醒時段",
        text="\n🍞 小提醒：分鐘要設成 00 喔\n\n✨ 幫我選個新的提醒時段吧",
        actions=[
            DatetimePickerAction(
                label="選擇時段",
                data=chat_payload["chat_id"],
                mode="time",
                initial=chat_payload["current_slot"],
            )
        ],
    )
    msg = TemplateMessage(altText="⚙️ 更改提醒時段 ⚠️ 輸入無效，請重新選擇提醒時段", template=template)
    return msg
