from datetime import datetime, timedelta
from string import Template

from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import (
    ButtonsTemplate,
    DatetimePickerAction,
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
    FlexText,
    MessageAction,
    TemplateMessage,
    TextMessage,
)

from routine_bot.constants import FREE_PLAN_MAX_EVENTS, TZ_TAIPEI
from routine_bot.models import EventData

# ------------------------------ Util Functions ------------------------------ #


def flex_text_bold_line(text: str) -> FlexText:
    return FlexText(text=text, size="md", weight="bold")


def flex_text_normal_line(text: str) -> FlexText:
    return FlexText(text=text, size="sm", color="#444444")


def flex_bubble_template(title: str, lines: list[str]) -> FlexBubble:
    contents = [flex_text_bold_line(title), FlexSeparator()]
    for line in lines:
        contents.append(flex_text_normal_line(line))

    bubble = FlexBubble(
        body=FlexBox(
            layout="vertical",
            paddingTop="lg",
            paddingBottom="lg",
            paddingStart="xl",
            paddingEnd="xl",
            spacing="lg",
            contents=contents,
        ),
    )
    return bubble


def parse_time_delta(timedelta_: relativedelta) -> str:
    time_diff = ""
    if timedelta_.years:
        time_diff = f"{timedelta_.years} 年"
    if timedelta_.months:
        time_diff = f"{time_diff} {timedelta_.months} 個月"
    if timedelta_.weeks:
        time_diff = f"{time_diff} {timedelta_.weeks} 週"
    if timedelta_.days:
        time_diff = f"{time_diff} {timedelta_.days} 日"
    return time_diff.lstrip()


# ----------------------------- Message Builders ------------------------------ #


class NewEvent:
    @staticmethod
    def prompt_for_event_name() -> TextMessage:
        return TextMessage(text="🎯 請輸入欲新增的事件名稱（限 2 至 20 字元）")

    @staticmethod
    def select_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text="\n⬇️ 請選擇事件起始日期",
            actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇事件起始日期", template=template
        )
        return msg

    @staticmethod
    def enable_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⬇️ 請選擇是否設定提醒",
            actions=[
                MessageAction(label="是", text="設定提醒"),
                MessageAction(label="否", text="不設定提醒"),
            ],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇是否設定提醒", template=template
        )
        return msg

    @staticmethod
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

    @staticmethod
    def event_cycle_example() -> FlexMessage:
        bubble = flex_bubble_template(
            title="🌟 自訂週期輸入格式",
            lines=["支援以下格式：", "📌 3 day", "📌 2 week", "📌 1 month", "⚠️ 請直接輸入上述其中一種格式"],
        )
        return FlexMessage(altText="➡️ 輸入自訂週期", contents=bubble)

    @staticmethod
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

    @staticmethod
    def event_created_with_reminder(chat_payload: dict[str, str]) -> FlexMessage:
        bubble = flex_bubble_template(
            title="✅ 新增完成！",
            lines=[
                f"🎯 新事件［{chat_payload['event_name']}］",
                f"🗓 起始日期：{chat_payload['start_date'][:10]}",
                f"🔁 事件週期：{chat_payload['event_cycle']}",
            ],
        )
        return FlexMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］✅ 新增完成！", contents=bubble)

    @staticmethod
    def invalid_input_for_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text="\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請透過下方按鈕選擇事件起始日期",
            actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請再次選擇事件起始日期", template=template
        )
        return msg

    @staticmethod
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
            altText=f"🎯 新事件［{chat_payload['event_name']}］ ⚠️ 輸入無效，請再次選擇是否設定提醒", template=template
        )
        return msg

    @staticmethod
    def invalid_input_for_event_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請選擇提醒週期",
            actions=[
                MessageAction(label="1 天", text="1 day"),
                MessageAction(label="1 週", text="1 week"),
                MessageAction(label="1 個月", text="1 month"),
                MessageAction(label="輸入自訂週期（點我看範例）", text="example"),
            ],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請再次選擇提醒週期", template=template
        )
        return msg


class FindEvent:
    @staticmethod
    def prompt_for_event_name() -> TextMessage:
        return TextMessage(text="🎯 請輸入欲查詢的事件名稱")

    @staticmethod
    def format_event_summary(event: EventData, recent_update_times: list[datetime]) -> FlexMessage:
        contents = [flex_text_bold_line(f"🎯［{event.event_name}］的事件摘要"), FlexSeparator()]
        if event.reminder_enabled:
            contents.append(flex_text_normal_line(f"⏰ 事件間隔：{event.event_cycle}"))
            contents.append(flex_text_normal_line(f"🔔 下次預計：{event.next_due_at.strftime('%Y-%m-%d')}"))
        else:
            contents.append(flex_text_normal_line("🔕 提醒設定：關閉"))
        contents.append(FlexSeparator())
        contents.append(flex_text_bold_line("🗓 最近完成日期"))
        for t in recent_update_times:
            contents.append(flex_text_normal_line(f"✅ {t.strftime('%Y-%m-%d')}"))

        bubble = FlexBubble(
            body=FlexBox(
                layout="vertical",
                paddingTop="lg",
                paddingBottom="lg",
                paddingStart="xl",
                paddingEnd="xl",
                spacing="lg",
                contents=contents,
            ),
        )
        msg = FlexMessage(altText=f"🎯［{event.event_name}］的事件摘要", contents=bubble)
        return msg


class Error:
    @staticmethod
    def unrecognized_command() -> TextMessage:
        return TextMessage(text="指令無法辨識🤣 請再試一次😌")

    @staticmethod
    def unexpected_error() -> TextMessage:
        return TextMessage(text="發生未預期的錯誤🚨 請再試一次或聯繫客服🛠️")

    @staticmethod
    def event_name_duplicated(event_name: str) -> TextMessage:
        return TextMessage(text=f"已有叫做［{event_name}］的事件🤣 請換個名稱再試一次😌")

    @staticmethod
    def event_name_not_found(event_name: str) -> TextMessage:
        return TextMessage(text=f"找不到叫做［{event_name}］的事件😱 請再試一次😌")

    @staticmethod
    def event_name_too_long() -> TextMessage:
        return TextMessage(text="事件名稱不可以超過 20 字元🤣 請再試一次😌")

    @staticmethod
    def event_name_too_short() -> TextMessage:
        return TextMessage(text="事件名稱不可以少於 2 字元🤣 請再試一次😌")

    @staticmethod
    def max_events_reached() -> FlexMessage:
        bubble = flex_bubble_template(
            title="⚠️ 無法新增事件",
            lines=[
                f"🔒 你已超過免費方案的 {FREE_PLAN_MAX_EVENTS} 個事件上限",
                "💡 你可以選擇：",
                "🗑️ 刪除超量事件，繼續使用免費方案",
                "🚀 升級至 premium，享受新增無上限",
            ],
        )
        msg = FlexMessage(altText="⚠️ 無法新增事件，請刪除超量事件或升級至 premium", contents=bubble)
        return msg

    @staticmethod
    def reminder_disabled() -> FlexMessage:
        bubble = flex_bubble_template(
            title="🔕 提醒功能已停用",
            lines=[
                f"🔒 你已超過免費方案的 {FREE_PLAN_MAX_EVENTS} 個事件上限",
                "💡 你可以選擇：",
                "🗑️ 刪除超量事件，恢復提醒功能",
                "🚀 升級至 premium，享受提醒無上限",
            ],
        )
        msg = FlexMessage(altText="🔕 提醒功能已停用，請刪除超量事件或升級至 premium", contents=bubble)
        return msg


class Greeting:
    @staticmethod
    def random() -> TextMessage:
        return TextMessage(text="hello!")


class Abort:
    @staticmethod
    def no_ongoing_chat() -> TextMessage:
        return TextMessage(text="沒有進行中的操作可以取消🤣")

    @staticmethod
    def ongoing_chat_aborted() -> TextMessage:
        return TextMessage(text="已中止目前的操作🙏\n請重新輸入新的指令😉")


class Reminder:
    @staticmethod
    def user_owned_event(event: EventData) -> FlexMessage:
        overdue_by = relativedelta(datetime.now(TZ_TAIPEI), event.next_due_at)
        overdue_by = parse_time_delta(overdue_by)

        lines = [
            f"✅ 上次完成：{event.last_done_at.strftime('%Y-%m-%d')}",
            f"🔁 事件間隔：{event.event_cycle}",
        ]
        if not overdue_by:
            lines.append(f"🗓️ 下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
            alt_text = f"⏰ 溫馨提醒～［{event.event_name}］已到預定的下次日期"
        else:
            lines.append(f"🗓️ 原定下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
            lines.append(f"⏳ 已超過原定間隔：{overdue_by}")
            alt_text = f"⏰ 溫馨提醒～［{event.event_name}］已超過原定間隔 {overdue_by}"

        bubble = flex_bubble_template(
            title=f"⏰ 是時候安排下次的［{event.event_name}］了！",
            lines=lines,
        )
        msg = FlexMessage(altText=alt_text, contents=bubble)
        return msg

    @staticmethod
    def shared_event(event: EventData, owner_profile: dict[str, str]) -> FlexMessage:
        overdue_by = relativedelta(datetime.now(TZ_TAIPEI), event.next_due_at)
        overdue_by = parse_time_delta(overdue_by)

        lines = [
            f"🫂 來自共享：{owner_profile.get('displayName')}",
            f"✅ 上次完成：{event.last_done_at.strftime('%Y-%m-%d')}",
            f"🔁 事件間隔：{event.event_cycle}",
        ]
        if not overdue_by:
            lines.append(f"🗓️ 下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
            alt_text = f"⏰ 溫馨提醒～［{event.event_name}］（來自{owner_profile.get('displayName')}）已到下次預計時間"
        else:
            lines.append(f"🗓️ 原定下次日期：{event.next_due_at.strftime('%Y-%m-%d')}")
            lines.append(f"⏳ 已超過原定間隔：{overdue_by}")
            alt_text = f"⏰ 溫馨提醒～［{event.event_name}］（來自{owner_profile.get('displayName')}）已超過原定間隔 {overdue_by}"

        bubble = flex_bubble_template(
            title=f"⏰ 是時候安排下次的［{event.event_name}］了！",
            lines=lines,
        )
        msg = FlexMessage(altText=alt_text, contents=bubble)
        return msg


class UserSettings:
    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
