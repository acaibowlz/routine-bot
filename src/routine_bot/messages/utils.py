from dateutil.relativedelta import relativedelta
from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexSeparator,
    FlexText,
)


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


def parse_time_delta(timedelta_: relativedelta) -> str:
    time_diff = ""
    if timedelta_.years:
        time_diff = f"{timedelta_.years} 年"
    if timedelta_.months:
        time_diff = f"{time_diff} {timedelta_.months} 個月"
    if timedelta_.weeks:
        time_diff = f"{time_diff} {timedelta_.weeks} 週"
    if timedelta_.days:
        time_diff = f"{time_diff} {timedelta_.days} 日"
    return time_diff.lstrip()
