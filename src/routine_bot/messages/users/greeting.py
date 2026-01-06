import random as r

from linebot.v3.messaging import TextMessage


def random() -> TextMessage:
    greetings = [
        "🌤️ 早安～又是幸福的一天～",
        "🍞 想起什麼要記的嗎？",
        "把今天也烤得酥酥脆脆吧 🍞",
        "💭 今天要寫什麼在吐司上呢",
        "要巧克力吐司、花生吐司還是草莓吐司 🍫",
        "請去做研究 📖",
        "我是你的記憶百寶袋 🧠",
        "🍞 今天有記得吃飯嗎",
        "🍞 每天都要維持 routine 呦！",
        "今天也要記得運動 💪",
        "💤 沒事早點睡，健康跟著你",
        "早安你好，吃早餐囉 🌤️",
        "離職掛嘴邊，自由在身邊 😄",
    ]
    return TextMessage(text=r.choice(greetings))
