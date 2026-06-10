# === PFAD-B FULL FILE: QGCR/states/airborne/subfsms/airborne_exit_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneExitFSM(BaseFSM):
    """
    AIRBORNE_EXIT:
    - Landung oder Rückkehr abgeschlossen
    - AirborneHFSM wechselt danach zu READY
    """

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_EXIT)
        self._next_state = AirborneSubState.AIRBORNE_EXIT

    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Airborne: EXIT (Landung abgeschlossen)")
            )
        except Exception:
            pass

    def _on_during(self):
        # EXIT bleibt EXIT
        self._next_state = AirborneSubState.AIRBORNE_EXIT

    def _on_exit(self):

        if self.active_substate == AirborneSubState.AIRBORNE_EXIT:
            self._next_state = MainState.READY

        return self._next_state
