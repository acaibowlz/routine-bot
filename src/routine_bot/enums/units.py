from enum import StrEnum, auto


class CycleUnit(StrEnum):
    DAY = auto()
    WEEK = auto()
    MONTH = auto()


SUPPORTED_UNITS = {unit.value for unit in CycleUnit}
