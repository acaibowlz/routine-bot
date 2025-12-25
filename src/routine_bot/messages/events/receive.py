from linebot.v3.messaging import FlexMessage

from routine_bot.constants import TZ_TAIPEI
from routine_bot.messages.utils import flex_bubble_template
from routine_bot.models import EventData


def enter_share_code():
    bubble = flex_bubble_template(title="🍞 接收共享事項", lines=["📝 請輸入分享碼"])
    return FlexMessage(altText="🍞 接收共享事項", contents=bubble)


def succeeded(event: EventData, owner_name: str) -> FlexMessage:
    if event.next_due_at is None:
        raise AttributeError(f"Event does not have a valid next due date: {event.event_id}")
    bubble = flex_bubble_template(
        title=f"🍞 成功共享［{event.event_name}］",
        lines=[
            f"👥 來自{owner_name}的共享提醒",
            f"🔜 下次時間：{event.next_due_at.astimezone(tz=TZ_TAIPEI).strftime('%Y-%m-%d')}",
            f"🔁 重複週期：{event.event_cycle}",
        ],
    )
    return FlexMessage(altText=f"🍞 成功共享［{event.event_name}］", contents=bubble)


def invalid_share_code() -> FlexMessage:
    bubble = flex_bubble_template(
        title="❌ 無效的分享碼", lines=["💭 無法辨認提供的分享碼", "🍞 請跟分享者再確認一次吧～"]
    )
    return FlexMessage(altText="❌ 無效的分享碼", contents=bubble)
