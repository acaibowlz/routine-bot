from enum import StrEnum, auto

# ------------------------------ Command Enums ------------------------------- #


class Command(StrEnum):
    NEW = "/new"
    FIND = "/find"
    UPDATE = "/update"
    EDIT = "/edit"
    DELETE = "/delete"
    VIEW = "/view"
    ABORT = "/abort"
    SETTINGS = "/settings"
    # premium features
    UPGRADE = "/upgrade"
    SHARE = "/share"
    DOWNGRADE = "/downgrade"


SUPPORTED_COMMANDS = {command.value for command in Command}

# -------------------------------- Chat Enums -------------------------------- #


class ChatType(StrEnum):
    NEW_EVENT = auto()
    FIND_EVENT = auto()
    UPDATE_EVENT = auto()
    EDIT_EVENT = auto()
    DELETE_EVENT = auto()
    USER_SETTINGS = auto()


class ChatStatus(StrEnum):
    ONGOING = auto()
    COMPLETED = auto()
    ABORTED = auto()


# ------------------------- Cycle Units (for events) -------------------------- #


class CycleUnit(StrEnum):
    DAY = auto()
    WEEK = auto()
    MONTH = auto()


SUPPORTED_UNITS = {unit.value for unit in CycleUnit}


# ------------------------------- Event Steps -------------------------------- #


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


# ------------------------------- User Settings ------------------------------- #


class UserSettingsSteps(StrEnum):
    SELECT_OPTION = auto()
    SELECT_NEW_NOTIFICATION_SLOT = auto()


class UserSettingsOptions(StrEnum):
    NOTIFICATION_SLOT = auto()
