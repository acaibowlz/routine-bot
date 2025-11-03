from linebot.v3.messaging import TextMessage


def random() -> TextMessage:
    return TextMessage(text="hello!")
