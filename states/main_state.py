# === PFAD-B FULL FILE: QGCR/states/main_state.py ===

from enum import Enum, auto


class MainState(Enum):
    STARTUP = auto()
    READY = auto()
    MISSION = auto()
    AIRBORNE = auto()
