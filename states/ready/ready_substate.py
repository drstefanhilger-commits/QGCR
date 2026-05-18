# === PFAD-B FULL FILE: ready_substate.py ===

from enum import Enum, auto

class ReadySubState(Enum):
    READY_IDLE = auto()
    READY_TAKEOFF = auto()
    READY_MISSION = auto()
    READY_HEARTBEAT_LOST = auto()
