# === PFAD-B FULL FILE: QGCR/states/airborne/subfsms/airborne_land_done_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneLandDoneFSM(BaseFSM):
    """
    AIRBORNE_LAND_DONE:
    - Landung erfolgreich abgeschlossen
    - Keine weitere Logik
    - AirborneHFSM entscheidet High-Level-Wechsel (zurück zu READY)
    """

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_LAND_DONE)
        self._next_state = AirborneSubState.AIRBORNE_LAND_DONE

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Landung abgeschlossen – System kehrt zu READY zurück")
            )
        except Exception:
            pass

        try:
            self.model.queue_registry.require("gui").push(
                ("log", "AIRBORNE: Landing complete (Exit)")
            )
        except Exception:
            pass

        self._next_state = AirborneSubState.AIRBORNE_LAND_DONE

    def _on_during(self):
        """
        Keine Aktionen – Exit-State bleibt stabil.
        """
        self._next_state = AirborneSubState.AIRBORNE_LAND_DONE

    def _on_exit(self):
        return self._next_state
