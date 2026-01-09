import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV")

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL", "")
SENDER_TOKEN = os.getenv("SENDER_TOKEN")

TZ_TAIPEI = ZoneInfo("Asia/Taipei")
FREE_PLAN_MAX_EVENTS = 5
