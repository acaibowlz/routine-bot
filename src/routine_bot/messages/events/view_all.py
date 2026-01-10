import ast

from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
    MessageAction,
    QuickReply,
    QuickReplyItem,
)

from routine_bot.enums.command import Command
from routine_bot.messages.utils import flex_text_bold_line, flex_text_normal_line


def format_all_events_summary(chat_payload: dict[str, str]) -> FlexMessage:
    event_summaries = ast.literal_eval(chat_payload["event_summaries"])
    if not event_summaries:
        contents = [
            flex_text_bold_line("👀 目前沒有任何事項"),
            FlexSeparator(),
            flex_text_normal_line("🍞 現在就來新增一筆紀錄吧！"),
        ]
        alt_text = "📋 所有事項一覽｜目前沒有任何紀錄 🍞"
    else:
        contents = [
            flex_text_bold_line("📋 所有事項一覽"),
            FlexSeparator(),
            flex_text_normal_line(f"🔍 共找到 {len(event_summaries)} 個事項"),
            FlexSeparator(),
        ]
        for i, event_summary in enumerate(event_summaries):
            contents.append(flex_text_bold_line(f"🍞 {event_summary['event_name']}"))
            if event_summary["owner_name"]:
                contents.append(flex_text_normal_line(f"👥 來自：{event_summary['owner_name']}"))
            contents.append(flex_text_normal_line(f"🗓 上次是：{event_summary['time_diff']}"))
            if event_summary["next_reminder"]:
                contents.append(flex_text_normal_line(f"🔔 下次提醒：{event_summary['next_reminder']}"))
            else:
                contents.append(flex_text_normal_line("🔕 提醒設定：關閉"))
            if i != len(event_summaries) - 1:
                contents.append(FlexSeparator())
        alt_text = f"📋 所有事項一覽｜共找到 {len(event_summaries)} 筆 🍞"

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
    msg = FlexMessage(
        altText=alt_text,
        contents=bubble,
        quickReply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="新增事項", text=Command.NEW.value)),
                QuickReplyItem(action=MessageAction(label="指令表", text=Command.MENU.value)),
            ]
        ),
    )
    return msg
