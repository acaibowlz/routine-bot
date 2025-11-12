from enum import StrEnum


class Command(StrEnum):
    NEW = "/new"
    FIND = "/find"
    DELETE = "/delete"
    VIEW_ALL = "/viewall"
    DONE = "/done"
    ABORT = "/abort"
    SETTINGS = "/settings"
    MENU = "/menu"
    HELP = "/help"


SUPPORTED_COMMANDS = {command.value for command in Command}
