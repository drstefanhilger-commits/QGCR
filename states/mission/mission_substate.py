# === PFAD-B FULL FILE: QGCR/states/mission/mission_substate.py ===

from enum import Enum, auto

class MissionSubState(Enum):
    MISSION_IDLE = auto()
    MISSION_UPLOAD = auto()
    MISSION_DOWNLOAD = auto()
