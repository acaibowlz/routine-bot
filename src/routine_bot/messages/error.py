from linebot.v3.messaging import TextMessage


def unexpected_error() -> TextMessage:
    return TextMessage(text="發生未預期的錯誤🚨 請再試一次或聯繫客服🛠️")
