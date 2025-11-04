from linebot.v3.messaging import (
    FlexMessage,
    MessageAction,
    QuickReply,
    QuickReplyItem,
)

from routine_bot.enums.command import Command
from routine_bot.messages.utils import flex_bubble_template, flex_text_bold_line, flex_text_normal_line


def format_welcome() -> FlexMessage:
    bubble = flex_bubble_template(
        title="🍞 歡迎使用記憶吐司",
        lines=[
            "嗨，我是記憶吐司 💭",
            "幫你記住那些生活裡容易被忽略的小事：",
            "上次運動是什麼時候？多久沒打掃？",
            "別擔心，我都幫你記下來～",
            "時間到我會出現提醒你，",
            "讓生活不再「拖延焦慮」，只有輕鬆節奏🌈",
        ],
    )

    msg = FlexMessage(
        altText="🍞 歡迎使用記憶吐司",
        contents=bubble,
        quickReply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="新增事項", text=Command.NEW.value)),
                QuickReplyItem(action=MessageAction(label="指令一覽表", text=Command.MENU.value)),
            ]
        ),
    )
    return msg
