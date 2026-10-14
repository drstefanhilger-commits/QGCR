# === PFAD-B FULL FILE: QGCR/states/airborne/subfsms/airborne_hold_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneHoldFSM(BaseFSM):
    """
    AIRBORNE_HOLD:
    - Drohne hält Position
    - Reagiert auf:
        * RESUME → AIRBORNE_MISSION
        * LAND → AIRBORNE_EXIT
        * Heartbeat verloren → AIRBORNE_LOST
    """

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_HOLD)
        self._next_state = AirborneSubState.AIRBORNE_HOLD
        self._pending_event = None

    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Airborne: HOLD")
            )
        except Exception:
            pass

    def _on_during(self):
        # 1) Heartbeat verloren → LOST
        if not self.model.px4_connected:
            self._next_state = AirborneSubState.AIRBORNE_LOST
            return

        # 2) GUI-Events lesen
        self._pending_event = None
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

        # 3) RESUME → zurück zu Mission
        if self._pending_event == "RESUME":
            self._next_state = AirborneSubState.AIRBORNE_MISSION
            return

        # 4) LAND → EXIT
        if self._pending_event == "LAND":
            self._next_state = AirborneSubState.AIRBORNE_EXIT
            return

        # 5) Standard: in HOLD bleiben
        self._next_state = AirborneSubState.AIRBORNE_HOLD

    def _on_exit(self):
        return self._next_state
