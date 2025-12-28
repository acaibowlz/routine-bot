from linebot.v3.messaging import FlexMessage

from routine_bot.messages.utils import flex_bubble_template


def enter_share_code():
    bubble = flex_bubble_template(title="🍞 接收共享事項", lines=["📝 請輸入分享碼"])
    return FlexMessage(altText="📝 請輸入分享碼", contents=bubble)


def succeeded(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title=f"✅ 成功共享［{chat_payload['event_name']}］",
        lines=[
            f"🍞 來自{chat_payload['owner_name']}的共享提醒",
            f"🔜 下次時間：{chat_payload['next_due_at']}",
            f"🔁 重複週期：{chat_payload['event_cycle']}",
        ],
    )
    return FlexMessage(altText=f"🍞 成功共享［{chat_payload['event_name']}］", contents=bubble)


def duplicated(chat_payload: dict[str, str]) -> FlexMessage:
    bubble = flex_bubble_template(
        title=f"⚠️ 已經設定過［{chat_payload['event_name']}］的共享權限囉",
        lines=["🍞 你已經設定過這個事項的共享權限囉", "🔔 重複週期結束時，你也會一起收到提醒"],
    )
    return FlexMessage(altText="", contents=bubble)


def invalid_share_code() -> FlexMessage:
    bubble = flex_bubble_template(
        title="❌ 無效的分享碼", lines=["💭 無法辨認提供的分享碼", "🍞 請跟分享者再確認一次吧～"]
    )
    return FlexMessage(altText="❌ 無效的分享碼", contents=bubble)
