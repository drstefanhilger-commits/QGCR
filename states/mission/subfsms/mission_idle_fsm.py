# === PFAD-B FULL FILE: QGCR/states/mission/subfsms/mission_idle_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.mission.mission_substate import MissionSubState


class MissionIdleFSM(BaseFSM):
    """
    MISSION_IDLE:
    - Wartet auf Benutzerinteraktion
    - Keine automatische Logik
    - Keine MAVLink-Verarbeitung
    - Substate bleibt stabil, bis MissionHFSM einen Wechsel auslöst
    """

    def __init__(self, model):
        super().__init__(model, MissionSubState.MISSION_IDLE)
        self._next_state = MissionSubState.MISSION_IDLE

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Mission: IDLE")
            )
        except Exception:
            pass

    def _on_during(self):
        """
        IDLE macht nichts.
        Gibt None zurück → kein Substate-Wechsel.
        """
        self._next_state = MissionSubState.MISSION_IDLE

    def _on_exit(self):
        return self._next_state
