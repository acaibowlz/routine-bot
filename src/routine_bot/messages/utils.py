from datetime import datetime

from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import FlexBox, FlexBubble, FlexSeparator, FlexText


def flex_text_bold_line(text: str) -> FlexText:
    return FlexText(text=text, size="md", weight="bold", lineSpacing="10px", wrap=True)


def flex_text_normal_line(text: str) -> FlexText:
    return FlexText(text=text, size="sm", color="#444444", lineSpacing="10px", wrap=True)


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
