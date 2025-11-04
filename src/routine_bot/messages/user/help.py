from linebot.v3.messaging import FlexMessage

from routine_bot.messages.utils import flex_bubble_template


def format_help():
    bubble = flex_bubble_template(
        title="💭 使用說明",
        lines=[
            "以下是我會的指令⬇️",
            "📝 新增與查找",
            "/new ➜ 新增一件要記的事情",
            "/find ➜ 查詢事項與相關的紀錄",
            "🗂️ 管理事項",
            "/delete ➜ 刪除不需要的事項",
            "/viewall ➜ 查看目前所有記得的事項",
            "🧭 其他功能",
            "/abort ➜ 取消目前的操作",
            "/settings ➜ 編輯設定",
            "/menu ➜ 顯示主選單",
            "/help ➜ 顯示這份說明（也就是現在這裡🍞）",
        ],
    )

    msg = FlexMessage(altText="💭 使用說明", contents=bubble)
    return msg
