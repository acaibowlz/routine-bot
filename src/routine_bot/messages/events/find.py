from datetime import datetime
from enum import StrEnum, auto

from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
)

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import (
    flex_bubble_template,
    flex_text_bold_line,
    flex_text_normal_line,
    get_verbal_time_diff,
)
from routine_bot.models import EventData


class FindEventSteps(StrEnum):
    INPUT_NAME = auto()


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(title="🍞 查詢事項", lines=["📝 請輸入要查詢的事項名稱"])
    return FlexMessage(altText="🍞 請輸入要查詢的事項名稱", contents=bubble)


def format_event_summary(event: EventData, recent_update_times: list[datetime]) -> FlexMessage:
    contents = [
        flex_text_bold_line(f"🍞［{event.event_name}］的摘要"),
        FlexSeparator(),
    ]
    time_diff = get_verbal_time_diff(
        datetime.today().astimezone(TZ_TAIPEI),
        event.last_done_at.astimezone(tz=TZ_TAIPEI),
    )
    contents.append(flex_text_normal_line(f"🗓 上次是：{time_diff}"))

    if event.reminder_enabled:
        if event.next_due_at is None:
            raise AttributeError(f"Event does not have a valid next due date: {event.event_id}")

        contents.append(flex_text_normal_line(f"🔁 重複週期：{event.event_cycle}"))
        contents.append(
            flex_text_normal_line(f"🔔 下次提醒：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}")
        )
    else:
        contents.append(flex_text_normal_line("🔕 提醒設定：關閉"))

    contents.append(FlexSeparator())
    contents.append(flex_text_bold_line("🗓 最近紀錄"))

    if recent_update_times:
        for t in recent_update_times:
            contents.append(flex_text_normal_line(f"✅ {t.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}"))
    else:
        contents.append(flex_text_normal_line("👀 目前還沒有任何紀錄"))

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
    msg = FlexMessage(altText=f"🍞［{event.event_name}］的摘要", contents=bubble)
    return msg
