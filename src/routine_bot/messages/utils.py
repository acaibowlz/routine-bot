
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
