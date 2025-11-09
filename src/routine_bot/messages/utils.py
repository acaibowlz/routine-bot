from datetime import datetime

from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import FlexBox, FlexBubble, FlexSeparator, FlexText


def flex_text_bold_line(text: str) -> FlexText:
    return FlexText(text=text, size="md", weight="bold")


def flex_text_normal_line(text: str) -> FlexText:
    return FlexText(text=text, size="sm", color="#444444")


def flex_bubble_template(title: str, lines: list[str]) -> FlexBubble:
    contents = [flex_text_bold_line(title), FlexSeparator()]
    for line in lines:
        contents.append(flex_text_normal_line(line))

    bubble = FlexBubble(
        body=FlexBox(
            layout="vertical",
            paddingTop="lg",
            paddingBottom="lg",
            paddingStart="xl",
            paddingEnd="xl",
            spacing="lg",
            contents=contents,
        ),
    )
    return bubble


def get_verbal_time_diff(dt1: datetime, dt2: datetime) -> str:
    """
    Get the verbal expression of the date difference.

    If there is no date difference, a simple "今天" will be returned. Otherwise, the two largest units will be returned.

    If `dt2` is earlier than `dt1`, the character "前" will be suffixed.
    """
    time_delta = relativedelta(dt1, dt2)

    parts = []
    if time_delta.years:
        parts.append(f"{time_delta.years} 年")
    if time_delta.months:
        parts.append(f"{time_delta.months} 個月")
    if time_delta.weeks:
        parts.append(f"{time_delta.weeks} 週")
    if time_delta.days:
        parts.append(f"{time_delta.days} 天")

    if not parts:
        time_diff = "今天"
    elif len(parts) == 1:
        time_diff = parts[0]
    else:
        time_diff = "又 ".join([" ".join(parts[:-1]), parts[-1]])
    if dt2 < dt1:
        return f"{time_diff}前"
    return time_diff
