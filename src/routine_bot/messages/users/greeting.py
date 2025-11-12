import random as r

from linebot.v3.messaging import TextMessage


def random() -> TextMessage:
    greetings = [
        "🌤️ 早安～又是幸福的一天～",
        "🍞 想起什麼要記的嗎？",
        "每天都值得好好紀錄下來呢 🌿",
        "容易忘記的瑣事就交給我吧 💪",
        "記憶我負責，行動就交給你 🧠",
        "把今天也烤得酥酥脆脆吧 🍞",
    ]
    return TextMessage(text=r.choice(greetings))
