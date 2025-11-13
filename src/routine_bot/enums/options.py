from enum import StrEnum, auto


class EditEventOptions(StrEnum):
    NAME = auto()
    REMINDER = auto()
    EVENT_CYCLE = auto()


class UserSettingsOptions(StrEnum):
    TIME_SLOT = auto()
