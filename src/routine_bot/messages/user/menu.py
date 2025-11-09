from linebot.v3.messaging import FlexMessage, MessageAction, QuickReply, QuickReplyItem

from routine_bot.enums.command import Command
from routine_bot.messages.utils import flex_bubble_template

items = [
    QuickReplyItem(action=MessageAction(label="新增事項", text=Command.NEW.value)),
    QuickReplyItem(action=MessageAction(label="查詢事項", text=Command.FIND.value)),
    # QuickReplyItem(action=MessageAction(label="更新事項完成日期", text="/update")),
    # QuickReplyItem(action=MessageAction(label="編輯事項", text="/edit")),
    QuickReplyItem(action=MessageAction(label="刪除事項", text=Command.DELETE.value)),
    QuickReplyItem(action=MessageAction(label="瀏覽所有事項", text=Command.VIEW_ALL.value)),
    QuickReplyItem(action=MessageAction(label="編輯設定", text=Command.SETTINGS.value)),
    QuickReplyItem(action=MessageAction(label="指令一覽", text=Command.MENU.value)),
    QuickReplyItem(action=MessageAction(label="使用說明", text=Command.HELP.value)),
]


def format_menu() -> FlexMessage:
    bubble = flex_bubble_template(title="📋 指令一覽表", lines=["⬇️ 使用下方的快速回覆按鈕來選擇指令！"])
    msg = FlexMessage(altText="📋 指令一覽表", contents=bubble, quickReply=QuickReply(items=items))
    return msg
