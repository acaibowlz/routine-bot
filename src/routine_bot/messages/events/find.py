from datetime import datetime
from enum import StrEnum, auto

from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
    TextMessage,
)

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import flex_text_bold_line, flex_text_normal_line, parse_time_delta
from routine_bot.models import EventData


class FindEventSteps(StrEnum):
    INPUT_NAME = auto()


def prompt_for_event_name() -> TextMessage:
    return TextMessage(text="請輸入你要查詢的事項名稱 ✨")


def format_event_summary(event: EventData, recent_update_times: list[datetime]) -> FlexMessage:
    contents = [
        flex_text_bold_line(f"🍞 吐司摘要［{event.event_name}］"),
        FlexSeparator(),
    ]
    time_delta = relativedelta(
        datetime.today().astimezone(TZ_TAIPEI),
        event.last_done_at.astimezone(tz=TZ_TAIPEI),
    )
    contents.append(flex_text_normal_line(f"🗓 上次是：{parse_time_delta(time_delta)}前"))

    if event.reminder_enabled:
        if event.next_due_at is None:
            raise AttributeError(f"Event {event.event_id} has reminder enabled, but the next due date cannot be found")
        contents.append(flex_text_normal_line(f"🔁 重複週期：{event.event_cycle}"))
        contents.append(
            flex_text_normal_line(f"🔔 下次提醒：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}")
        )
    else:
        contents.append(flex_text_normal_line("🔕 提醒狀態：關閉"))

    contents.append(FlexSeparator())
    contents.append(flex_text_bold_line("🗓 最近完成"))

    if recent_update_times:
        for t in recent_update_times:
            contents.append(flex_text_normal_line(f"✅ {t.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}"))
    else:
        contents.append(flex_text_normal_line("👀 目前還沒有完成紀錄"))

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
    msg = FlexMessage(altText=f"🍞 吐司摘要［{event.event_name}］", contents=bubble)
    return msg
