# === PFAD-B FULL FILE: QGCR/states/airborne/subfsms/airborne_lost_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneLostFSM(BaseFSM):
    """
    AIRBORNE_LOST:
    - Telemetrie oder GPS verloren
    - Bleibt in LOST, bis AirborneHFSM High-Level-Wechsel macht
    """

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_LOST)
        self._next_state = AirborneSubState.AIRBORNE_LOST

    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Airborne: LOST (Failsafe)")
            )
        except Exception:
            pass

    def _on_during(self):
        # LOST bleibt LOST
        self._next_state = AirborneSubState.AIRBORNE_LOST

    def _on_exit(self):
        return self._next_state
