from linebot.v3.messaging import FlexMessage

from routine_bot.enums.command import Command
from routine_bot.messages.utils import flex_bubble_template


def format_help():
    bubble = flex_bubble_template(
        title="💭 使用說明",
        lines=[
            "以下是我會的指令⬇️",
            "📝 新增與查找",
            f"{Command.NEW.value} ➜ 新增一件要記的事情",
            f"{Command.DONE.value} ➜ 新增事項的完成紀錄",
            f"{Command.FIND.value} ➜ 查詢事項與相關的紀錄",
            "🗂️ 管理事項",
            f"{Command.EDIT.value} ➜ 編輯事項內容",
            f"{Command.DELETE.value} ➜ 刪除不需要的事項",
            f"{Command.VIEW_ALL.value} ➜ 瀏覽目前所有記得的事項",
            "🧭 其他功能",
            f"{Command.ABORT.value} ➜ 取消目前進行中的操作",
            f"{Command.SETTINGS.value} ➜ 編輯設定",
            f"{Command.MENU.value} ➜ 顯示主選單",
            f"{Command.HELP.value} ➜ 顯示這份說明（現在這裡🍞）",
        ],
    )

    msg = FlexMessage(altText="💭 使用說明", contents=bubble)
    return msg
