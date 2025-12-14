from linebot.v3.messaging import FlexMessage

from routine_bot.messages.utils import flex_bubble_template


def event_cycle_example() -> FlexMessage:
    bubble = flex_bubble_template(
        title="🌟 自訂週期輸入格式",
        lines=[
            "支援以下格式：",
            "📌 3 day",
            "📌 2 week",
            "📌 1 month",
            "⚠️ 請直接輸入上述其中一種格式",
        ],
    )
    return FlexMessage(altText="✨ 請輸入循環週期", contents=bubble)
