# === PFAD-B FULL FILE: QGCR/states/airborne/subfsms/airborne_land_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneLandFSM(BaseFSM):
    """
    AIRBORNE_LAND:
    - Führt eine Landesequenz aus (nicht-blockierend)
    - Delegiert an Landing-MicroService
    - Bei Erfolg → AIRBORNE_LAND_DONE
    - Bei Fehler → AIRBORNE_ERROR
    """

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_LAND)
        self._next_state = AirborneSubState.AIRBORNE_LAND

        # Landing-MicroService
        self.ms = self.model.services.landing

        # Event-Puffer
        self._pending_event = None

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Airborne: Landung eingeleitet")
            )
        except Exception:
            pass

        try:
            self.model.queue_registry.require("gui").push(
                ("log", "AIRBORNE: Landing sequence started")
            )
        except Exception:
            pass

        # Landing starten
        try:
            self.ms.start()
        except Exception:
            pass

    def _on_during(self):
        """
        Landesequenz tickt nicht-blockierend.
        """

        # 1) Heartbeat verloren → ERROR
        if not self.model.px4_connected:
            self._next_state = AirborneSubState.AIRBORNE_ERROR
            return

        # 2) Landing tick
        self.ms.tick()

        # 3) Fehler?
        if self.ms.error:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", f"Landung FEHLER: {self.ms.error}")
                )
            except Exception:
                pass

            try:
                self.model.queue_registry.require("gui").push(
                    ("log", f"AIRBORNE: Landing error: {self.ms.error}")
                )
            except Exception:
                pass

            self._next_state = AirborneSubState.AIRBORNE_ERROR
            return

        # 4) Landung abgeschlossen?
        if self.ms.done:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", "Landung abgeschlossen")
                )
            except Exception:
                pass

            try:
                self.model.queue_registry.require("gui").push(
                    ("log", "AIRBORNE: Landing complete")
                )
            except Exception:
                pass

            self._next_state = AirborneSubState.AIRBORNE_LAND_DONE
            return

        # 5) Standard: im LAND bleiben
        self._next_state = AirborneSubState.AIRBORNE_LAND

    def _on_exit(self):
        return self._next_state
