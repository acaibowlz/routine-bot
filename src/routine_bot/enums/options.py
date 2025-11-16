from enum import StrEnum


class NewEventReminderOptions(StrEnum):
    ENABLE = "設定提醒"
    DISABLE = "不設定提醒"


class ConfirmDeletionOptions(StrEnum):
    DELETE = "刪除事項"
    CANCEL = "取消刪除"


class ToggleReminderOptions(StrEnum):
    CONFIRM = "是，修改設定"
    CANCEL = "不用，維持現狀"


class EditEventOptions(StrEnum):
    NAME = "名稱"
    REMINDER = "提醒設定"
    EVENT_CYCLE = "重複週期"


class UserSettingsOptions(StrEnum):
    TIME_SLOT = "提醒時段"
