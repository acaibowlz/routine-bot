from enum import StrEnum, auto


class ChatType(StrEnum):
    NEW_EVENT = auto()
    FIND_EVENT = auto()
    DELETE_EVENT = auto()
    DONE_EVENT = auto()
    EDIT_EVENT = auto()
    SHARE_EVENT = auto()
    RECEIVE_EVENT = auto()
    REVOKE_EVENT = auto()
    USER_SETTINGS = auto()


class ChatStatus(StrEnum):
    ONGOING = auto()
    COMPLETED = auto()
    ABORTED = auto()
