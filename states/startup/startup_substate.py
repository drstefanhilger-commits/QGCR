# === PFAD-B FULL FILE: QGCR/states/startup_substate.py ===

from enum import Enum, auto


class StartupSubState(Enum):
    """
    Substates für die sequenzielle Startup-Pipeline:
        STARTUP_HEARTBEAT → STARTUP_PARAMS → STARTUP_HOME → STARTUP_MISSION → STARTUP_OK
    """

    STARTUP_HEARTBEAT = auto()
    STARTUP_PARAMS = auto()
    STARTUP_HOME = auto()
    STARTUP_MISSION = auto()
    STARTUP_OK = auto()
