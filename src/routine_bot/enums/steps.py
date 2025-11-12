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


class DoneEventSteps(StrEnum):
    INPUT_NAME = auto()
    SELECT_DONE_DATE = auto()


class UserSettingsSteps(StrEnum):
    SELECT_OPTION = auto()
    SELECT_NEW_TIME_SLOT = auto()
