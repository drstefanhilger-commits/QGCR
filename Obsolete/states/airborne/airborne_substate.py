# === PFAD-B FULL FILE: airborne_substate.py ===

from enum import Enum, auto


class AirborneSubState(Enum):
    """
    Substates für den Airborne-Modus.
    """
    AIRBORNE_TAKEOFF = auto()
    AIRBORNE_MISSION = auto()
    AIRBORNE_HOLD = auto()
    AIRBORNE_LOST = auto()
    AIRBORNE_EXIT = auto()
    AIRBORNE_RESET = auto()

