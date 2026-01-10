from enum import StrEnum, auto

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
from routine_bot.messages.utils import (
    flex_bubble_template,
    flex_text_bold_line,
    flex_text_normal_line,
)


class FindEventSteps(StrEnum):
    INPUT_NAME = auto()


def enter_event_name() -> FlexMessage:
    bubble = flex_bubble_template(
        title="🍞 查詢事項", lines=["📝 請輸入要查詢的事項名稱", "❗ 只能查詢由自己新增的事項哦"]
    )
    return FlexMessage(altText="📝 請輸入要查詢的事項名稱", contents=bubble)


def format_event_info(chat_payload: dict[str, str]) -> FlexMessage:
    contents = [
        flex_text_bold_line(f"🍞［{chat_payload['event_name']}］的摘要"),
        FlexSeparator(),
        flex_text_normal_line(f"🗓 上次是：{chat_payload['time_diff']}"),
    ]
    if chat_payload["reminder"] == "True":
        contents.append(flex_text_normal_line(f"🔁 重複週期：{chat_payload['event_cycle']}"))
        contents.append(flex_text_normal_line(f"🔔 下次提醒：{chat_payload['next_due_at']}"))
    else:
        contents.append(flex_text_normal_line("🔕 提醒設定：關閉"))

    contents.append(FlexSeparator())
    contents.append(flex_text_bold_line("🗓 最近紀錄"))

    if chat_payload["recent_records"]:
        for record in chat_payload["recent_records"]:
            contents.append(flex_text_normal_line(f"✅ {record}"))
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
    msg = FlexMessage(
        altText=f"🍞［{chat_payload['event_name']}］的摘要",
        contents=bubble,
        quickReply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="新增事項", text=Command.NEW.value)),
                QuickReplyItem(action=MessageAction(label="編輯事項", text=Command.EDIT.value)),
                QuickReplyItem(action=MessageAction(label="指令表", text=Command.MENU.value)),
            ]
        ),
    )
    return msg
