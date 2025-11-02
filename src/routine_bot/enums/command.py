from enum import StrEnum


class Command(StrEnum):
    NEW = "/new"
    FIND = "/find"
    DELETE = "/delete"
    VIEW_ALL = "/viewall"
    ABORT = "/abort"
    SETTINGS = "/settings"


SUPPORTED_COMMANDS = {command.value for command in Command}
