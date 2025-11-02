from enum import StrEnum, auto


class NewEventSteps(StrEnum):
    INPUT_NAME = auto()
    SELECT_START_DATE = auto()
    ENABLE_REMINDER = auto()
    SELECT_EVENT_CYCLE = auto()


class FindEventSteps(StrEnum):
    INPUT_NAME = auto()


class DeleteEventSteps(StrEnum):
    INPUT_NAME = auto()
    CONFIRM_DELETION = auto()


class UserSettingsSteps(StrEnum):
    SELECT_OPTION = auto()
    SELECT_NEW_NOTIFICATION_SLOT = auto()
