from enum import StrEnum, auto


class NewEventSteps(StrEnum):
    ENTER_NAME = auto()
    SELECT_START_DATE = auto()
    ENTER_REMINDER_OPTION = auto()
    ENTER_EVENT_CYCLE = auto()


class FindEventSteps(StrEnum):
    ENTER_NAME = auto()


class DeleteEventSteps(StrEnum):
    ENTER_NAME = auto()
    CONFIRM_DELETION = auto()


class DoneEventSteps(StrEnum):
    ENTER_NAME = auto()
    SELECT_DONE_DATE = auto()


class EditEventSteps(StrEnum):
    ENTER_NAME = auto()
    SELECT_OPTION = auto()
    ENTER_NEW_NAME = auto()
    TOGGLE_REMINDER = auto()
    ENTER_NEW_EVENT_CYCLE = auto()


class ShareEventSteps(StrEnum):
    ENTER_NAME = auto()


class ReceiveEventSteps(StrEnum):
    ENTER_NAME = auto()


class UserSettingsSteps(StrEnum):
    SELECT_OPTION = auto()
    SELECT_NEW_TIME_SLOT = auto()
