from enum import StrEnum


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
