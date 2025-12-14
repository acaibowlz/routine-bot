from linebot.v3.messaging import FlexMessage

from routine_bot.messages.utils import flex_bubble_template


def error(contents: list[str]) -> FlexMessage:
    bubble = flex_bubble_template(title="❌ 錯誤", lines=contents)
    return FlexMessage(altText="❌ 錯誤訊息", contents=bubble)


def unrecognized_command() -> FlexMessage:
    return error(["💭 嗯？這個指令我不太認識", "🍞 再試一次看看吧"])


def event_name_duplicated(event_name: str) -> FlexMessage:
    return error([f"💭 已經有叫做［{event_name}］的事項囉", "🍞 再想一個新名字試試吧"])


def event_name_not_found(event_name: str) -> FlexMessage:
    return error([f"💭 嗯？好像沒有叫做［{event_name}］的事項喔", "🍞 再試一次看看吧"])


def event_name_too_long() -> FlexMessage:
    return error(["💭 名字好像有點長呢～（限 10 個字以內喔）"])


def event_name_too_short() -> FlexMessage:
    return error(["💭 名字好像有點太短了", "🍞 再加入幾個字吧"])
