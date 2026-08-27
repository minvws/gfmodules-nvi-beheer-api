from enum import Enum, auto


class LoadStrategy(Enum):
    SELECTIN_LOAD = auto()
    OUTERJOIN_LOAD = auto()
