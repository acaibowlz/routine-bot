from datetime import datetime

from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
    MessageAction,
    QuickReply,
    QuickReplyItem,
)

from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums.command import Command
from routine_bot.messages.utils import flex_text_bold_line, flex_text_normal_line, get_verbal_time_diff
from routine_bot.models import EventData


def format_all_events_summary(events: list[EventData]) -> FlexMessage:
    if events:
        contents = [
            flex_text_bold_line("📋 所有事項一覽"),
            FlexSeparator(),
            flex_text_normal_line(f"🔍 共找到 {len(events)} 個事項"),
            FlexSeparator(),
        ]

        for i, event in enumerate(events):
            contents.append(flex_text_bold_line(f"🍞［{event.event_name}］"))
            time_diff = get_verbal_time_diff(
                datetime.today().astimezone(TZ_TAIPEI),
                event.last_done_at.astimezone(tz=TZ_TAIPEI),
            )
            contents.append(flex_text_normal_line(f"🗓 上次是：{time_diff}"))
            if event.reminder_enabled:
                if event.next_due_at is None:
                    raise AttributeError(f"The event '{event.event_name}' does not have a valid next due date.")
                contents.append(
                    flex_text_normal_line(
                        f"🔔 下次提醒：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}"
                    )
                )
            else:
                contents.append(flex_text_normal_line("🔕 提醒狀態：關閉"))
            if i != len(events) - 1:
                contents.append(FlexSeparator())
    else:
        contents = [
            flex_text_bold_line("👀 目前沒有任何事項"),
            FlexSeparator(),
            flex_text_normal_line("🍞 現在就來新增一筆紀錄吧！"),
        ]

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

    if events:
        msg = FlexMessage(altText=f"📋 所有事項一覽｜共找到 {len(events)} 筆 🍞", contents=bubble)
    else:
        msg = FlexMessage(
            altText="📋 所有事項一覽｜目前沒有任何紀錄 🍞",
            contents=bubble,
            quickReply=QuickReply(
                items=[QuickReplyItem(action=MessageAction(label="新增事項", text=Command.NEW.value))]
            ),
        )
    return msg
