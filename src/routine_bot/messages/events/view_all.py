from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
)

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import flex_text_bold_line, flex_text_normal_line
from routine_bot.models import EventData


def format_all_events_summary(events: list[EventData]) -> FlexMessage:
    contents = [
        flex_text_bold_line("📋 所有事件一覽"),
        FlexSeparator(),
        flex_text_normal_line(f"🔍 共找到 {len(events)} 個事件"),
        FlexSeparator(),
    ]

    for i, event in enumerate(events):
        contents.append(flex_text_bold_line(f"［{event.event_name}］"))
        contents.append(
            flex_text_normal_line(f"🗓 最近完成：{event.last_done_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}")
        )
        if event.reminder_enabled:
            if event.next_due_at is None:
                raise AttributeError(f"Event '{event.event_name}' is missing its next due date")
            contents.append(flex_text_normal_line(f"🔁 事件週期：{event.event_cycle}"))
            contents.append(
                flex_text_normal_line(f"🔔 下次預計：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}")
            )
        else:
            contents.append(flex_text_normal_line("🔕 提醒設定：關閉"))
        if i != len(events) - 1:
            contents.append(FlexSeparator())

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
    msg = FlexMessage(altText=f"📋 所有事件一覽 🔍 共找到 {len(events)} 個事件", contents=bubble)
    return msg
