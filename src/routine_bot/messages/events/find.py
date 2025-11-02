from datetime import datetime

from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
    TextMessage,
)

from routine_bot.messages.utils import flex_text_bold_line, flex_text_normal_line
from routine_bot.models import EventData


def prompt_for_event_name() -> TextMessage:
    return TextMessage(text="🎯 請輸入欲查詢的事件名稱")


def format_event_summary(event: EventData, recent_update_times: list[datetime]) -> FlexMessage:
    contents = [flex_text_bold_line(f"🎯［{event.event_name}］的事件摘要"), FlexSeparator()]
    if event.reminder_enabled:
        if event.next_due_at is None:
            raise AttributeError("Event's next due date is missing")
        contents.append(flex_text_normal_line(f"🔁 事件週期：{event.event_cycle}"))
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
