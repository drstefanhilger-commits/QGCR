# === PFAD-B FULL FILE: main_state.py ===

from enum import Enum, auto


class MainState(Enum):
    """
    High-Level States des Systems.
    Diese bilden die oberste Ebene der HFSM-Architektur.
    """

    READY = auto()       # Bodenphase, Idle, Preflight
    MISSION = auto()     # Missions-Upload/Download/Validation (Boden)
    AIRBORNE = auto()    # Flugphase
    LOST = auto()        # Fehlerzustand / Verbindung verloren
