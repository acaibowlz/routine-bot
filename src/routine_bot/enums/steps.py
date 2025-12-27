from enum import StrEnum, auto


class BaseSteps(StrEnum):
    COMPLETED = auto()


class NewEventSteps(StrEnum):
    ENTER_NAME = auto()
    SELECT_START_DATE = auto()
    ENTER_REMINDER_OPTION = auto()
    ENTER_EVENT_CYCLE = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class FindEventSteps(StrEnum):
    ENTER_NAME = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class DeleteEventSteps(StrEnum):
    ENTER_NAME = auto()
    CONFIRM_DELETION = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class DoneEventSteps(StrEnum):
    ENTER_NAME = auto()
    SELECT_DONE_DATE = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class EditEventSteps(StrEnum):
    ENTER_NAME = auto()
    SELECT_OPTION = auto()
    ENTER_NEW_NAME = auto()
    TOGGLE_REMINDER = auto()
    ENTER_NEW_EVENT_CYCLE = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class ShareEventSteps(StrEnum):
    ENTER_NAME = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class ReceiveEventSteps(StrEnum):
    ENTER_CODE = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class RevokeEventSteps(StrEnum):
    ENTER_NAME = auto()
    SELECT_RECIPIENT = auto()
    COMPLETED = BaseSteps.COMPLETED.value


class UserSettingsSteps(StrEnum):
    SELECT_OPTION = auto()
    SELECT_NEW_TIME_SLOT = auto()
    COMPLETED = BaseSteps.COMPLETED.value
