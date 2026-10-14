# === PFAD-B FULL FILE: QGCR/states/airborne/subfsms/airborne_reset_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneResetFSM(BaseFSM):
    """
    RESET-FSM für Fixed-Wing:
    - Startet ResetMicroService
    - Wartet auf done/error
    - Setzt reset_done Flag für MainController
    """

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_RESET)

        self._started = False

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def _on_enter(self):
        self.model.log.qgcr("[AIRBORNE_RESET] ENTER")

    # ------------------------------------------------------------
    # DURING
    # ------------------------------------------------------------
    def _on_during(self):

        # 1) ResetMicroService starten
        if not self._started:
            try:
                if hasattr(self.model, "reset") and self.model.reset is not None:
                    self.model.reset.start()
                    self._started = True
                    self.model.log.qgcr("[AIRBORNE_RESET] ResetMS gestartet")
                else:
                    self.model.log.qgcr("[AIRBORNE_RESET] ERROR: model.reset nicht vorhanden")
                    self.model.reset_done = True
            except Exception as e:
                self.model.log.qgcr(f"[AIRBORNE_RESET] ERROR beim Start: {e}")
                self.model.reset_done = True
            return None

        # 2) Auf Abschluss warten
        if getattr(self.model.reset, "done", False):
            self.model.log.qgcr("[AIRBORNE_RESET] ResetMS DONE")
            self._finish_reset()
            return None

        # 3) Fehler?
        if getattr(self.model.reset, "error", None):
            self.model.log.qgcr(f"[AIRBORNE_RESET] ResetMS ERROR: {self.model.reset.error}")
            self._finish_reset()
            return None

        # 4) Sonst weiter warten
        return None

    # ------------------------------------------------------------
    # EXIT
    # ------------------------------------------------------------
    def _on_exit(self):
        self.model.log.qgcr("[AIRBORNE_RESET] EXIT")

    # ------------------------------------------------------------
    # Hilfsfunktion
    # ------------------------------------------------------------
    def _finish_reset(self):
        """
        Setzt das Flag für MainController → READY
        """
        try:
            self.model.vehicle_alt = 0.0
            self.model.flight_active = False
            self.model.mission_active = False
            self.model.takeoff_in_progress = False

            try:
                self.model.hfsm_events.clear()
            except Exception:
                pass

            self.model.log.qgcr("[AIRBORNE_RESET] Model zurückgesetzt")
        except Exception as e:
            self.model.log.qgcr(f"[AIRBORNE_RESET] WARN: Model-Reset fehlgeschlagen: {e}")

        # MainController sieht dieses Flag im nächsten Tick
        self.model.reset_done = True
        self.model.log.qgcr("[AIRBORNE_RESET] model.reset_done = True")
