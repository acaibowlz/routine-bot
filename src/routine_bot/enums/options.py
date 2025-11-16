from enum import StrEnum, auto


class NewEventReminderOptions(StrEnum):
    ENABLE = "設定提醒"
    DISABLE = "不設定提醒"


class ConfirmDeletionOptions(StrEnum):
    DELETE = "刪除事項"
    CANCEL = "取消刪除"


class ToggleReminderOptions(StrEnum):
    CONFIRM = "是，修改設定"
    CANCEL = "否，保留目前設定"


class EditEventOptions(StrEnum):
    NAME = auto()
    REMINDER = auto()
    EVENT_CYCLE = auto()


class UserSettingsOptions(StrEnum):
    TIME_SLOT = auto()
