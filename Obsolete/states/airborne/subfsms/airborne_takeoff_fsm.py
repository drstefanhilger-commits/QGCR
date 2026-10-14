# === PFAD-B FULL FILE: QGCR/states/airborne/subfsms/airborne_takeoff_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneTakeoffFSM(BaseFSM):
    """
    AIRBORNE_TAKEOFF:
    - Startphase nach READY → AIRBORNE
    - Startet den TakeoffMicroService (nicht-blockierend)
    - Wechselt nach erfolgreichem Abheben zu AIRBORNE_MISSION
    - Heartbeat-Lost → AIRBORNE_LOST
    """

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_TAKEOFF)
        self._next_state = AirborneSubState.AIRBORNE_TAKEOFF
        self._started = False

    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Airborne: TAKEOFF")
            )
        except Exception:
            pass

        # TakeoffMicroService direkt aus dem Model starten
        try:
            if hasattr(self.model, "takeoff") and self.model.takeoff is not None:
                self.model.takeoff.start()
                self._started = True
                self.model.queue_registry.require("gui").push(
                    ("log", "TakeoffMicroService: START")
                )
            else:
                self.model.queue_registry.require("gui").push(
                    ("log", "TakeoffMicroService ERROR: model.takeoff nicht vorhanden")
                )
                self._next_state = AirborneSubState.AIRBORNE_LOST
        except Exception as e:
            try:
                self.model.queue_registry.require("gui").push(
                    ("log", f"TakeoffMicroService ERROR: {e}")
                )
            except Exception:
                pass
            self._next_state = AirborneSubState.AIRBORNE_LOST

    def _on_during(self):
        # 1) Heartbeat verloren → LOST
        if not self.model.px4_connected:
            self._next_state = AirborneSubState.AIRBORNE_LOST
            return

        # Wenn TakeoffMS nie gestartet wurde, im TAKEOFF bleiben
        if not self._started:
            self._next_state = AirborneSubState.AIRBORNE_TAKEOFF
            return

        # 2) MicroService fertig?
        if getattr(self.model.takeoff, "done", False):
            self._next_state = AirborneSubState.AIRBORNE_MISSION
            return

        # 3) MicroService Fehler?
        if getattr(self.model.takeoff, "error", None):
            self._next_state = AirborneSubState.AIRBORNE_LOST
            return

        # 4) Sonst im TAKEOFF bleiben
        self._next_state = AirborneSubState.AIRBORNE_TAKEOFF

    def _on_exit(self):
        return self._next_state
