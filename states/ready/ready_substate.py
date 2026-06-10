# === PFAD-B FULL FILE: QGCR/states/ready/ready_substate.py ===

from enum import Enum, auto

class ReadySubState(Enum):
    READY_IDLE = auto()
    READY_TAKEOFF = auto()
    READY_LAND = auto()
    READY_STOP = auto()
    READY_MISSION_START = auto()
    READY_RESET = auto()