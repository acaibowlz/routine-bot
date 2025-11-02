from enum import StrEnum, auto


class ChatType(StrEnum):
    NEW_EVENT = auto()
    FIND_EVENT = auto()
    DELETE_EVENT = auto()
    VIEW_ALL = auto()
    USER_SETTINGS = auto()


class ChatStatus(StrEnum):
    ONGOING = auto()
    COMPLETED = auto()
    ABORTED = auto()
