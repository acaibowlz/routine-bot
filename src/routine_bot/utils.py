import logging
import re
from dataclasses import dataclass
from datetime import datetime

import requests
from cachetools.func import ttl_cache
from dateutil.relativedelta import relativedelta

from routine_bot.constants import LINE_CHANNEL_ACCESS_TOKEN
from routine_bot.enums.units import SUPPORTED_UNITS


def format_logger_name(module_name: str) -> str:
    return module_name.split(".", maxsplit=1)[1]


logger = logging.getLogger(format_logger_name(__name__))


def _camel_to_snake(text):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


@dataclass
class UserProfile:
    user_id: str
    display_name: str
    language: str
    picture_url: str | None = None
    status_message: str | None = None


@ttl_cache(maxsize=None, ttl=600)
def get_user_profile(user_id: str) -> UserProfile:
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    logger.debug(f"Retrieved user profile for: {user_id}")
    return UserProfile(**{_camel_to_snake(key): val for key, val in resp.json().items()})


def sanitize_msg(text: str) -> str:
    """
    Cleans and normalizes user input text for consistent downstream processing.

    Steps:
    1. Trim leading/trailing whitespace and newlines
    2. Normalize Unicode (NFKC) — converts fullwidth to halfwidth, etc.
    3. Collapse multiple spaces/newlines
    4. Remove invisible control characters
    """
    if not text:
        return ""
    # text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    return text


def validate_event_name(event_name: str) -> list[str] | None:
    """
    Return None if the event name is valid, or the error message will be returned.
    """
    if len(event_name) < 2:
        return ["⚠️ 這個名字有點太短了～至少要有 2 個字喔！", "試試看長一點的名字吧 🍞"]
    if len(event_name) > 10:
        return ["⚠️ 這個名字有點太長了～最多只能 10 個字喔！", "試試看短一點的名字吧 🍞"]
    invalid_chars = re.findall(r"[^\u4e00-\u9fffA-Za-z0-9 _-]", event_name)
    if invalid_chars:
        invalid_chars = list(dict.fromkeys(invalid_chars))
        wrapped = "、".join([f"「{ch}」" for ch in invalid_chars])
        return [f"⚠️ 我不太認得這些字：{wrapped}", "換成一般文字或符號再試試吧 🍞"]
    return None


def parse_event_cycle(text: str) -> tuple[int | None, str | None]:
    try:
        value, unit = text.split(" ", maxsplit=1)
    except ValueError:
        return None, None
    try:
        value = int(value)
    except ValueError:
        return None, None
    if unit not in SUPPORTED_UNITS:
        return None, None
    return value, unit


def get_time_diff(dt1: datetime, dt2: datetime) -> str:
    """
    Get the verbal expression of the date difference.

    If there is no date difference, a simple "今天" will be returned. Otherwise, the largest unit will be returned.

    If `dt2` is earlier than `dt1`, the character "前" will be suffixed.
    """
    time_delta = relativedelta(dt1, dt2)
    if time_delta.years:
        time_diff = f"{time_delta.years} 年"
    elif time_delta.months:
        time_diff = f"{time_delta.months} 個月"
    elif time_delta.weeks:
        time_diff = f"{time_delta.weeks} 週"
    elif time_delta.days:
        time_diff = f"{time_delta.days} 天"
    else:
        time_diff = "今天"

    if dt2 < dt1:
        return f"{time_diff}前"
    return time_diff
