# === PFAD-B FULL FILE: QGCR/states/ready/subfsms/ready_takeoff_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState


class ReadyTakeoffFSM(BaseFSM):
    """
    READY_TAKEOFF:
    Delegiert die komplette Takeoff-Sequenz an TakeoffMicroService.
    - KEINE externen Events werden direkt verarbeitet
    - _on_during() sammelt nur Events und tickt den MicroService
    - _on_exit() entscheidet den Sub-State-Wechsel
    """

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_TAKEOFF)

        # MicroService: model.services.takeoff MUSS existieren
        self.ms = model.services.takeoff

        # Event-Puffer
        self._pending_event = None

        # Statusflags
        self._abort = False
        self._error = None
        self._done = False

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(("status", "Takeoff initiated"))
        except Exception:
            pass

        # Sequenz starten
        self.ms.start()

    def _on_during(self):
        """
        READY_TAKEOFF sammelt nur Informationen.
        Statewechsel passieren ausschließlich in _on_exit().
        """

        # GUI-Event lesen
        self._pending_event = None
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

        # Heartbeat verloren?
        if not self.model.px4_connected:
            self._error = "Heartbeat lost"
            return

        # Tab-Wechsel → Takeoff abbrechen
        if self._pending_event == "GUI_TAB_HOME":
            self._abort = True
            return

        # MicroService tick()
        self.ms.tick()

        # Fehler?
        if self.ms.error:
            self._error = self.ms.error
            return

        # Erfolg?
        if self.ms.done:
            self._done = True
            return

    def _on_exit(self):
        """
        EINZIGER Ort für Sub-State-Wechsel.
        """

        # 1) Heartbeat verloren → HEARTBEAT_LOST
        if self._error == "Heartbeat lost":
            return ReadySubState.READY_HEARTBEAT_LOST

        # 2) Tab-Wechsel → Abbruch → READY_IDLE
        if self._abort:
            try:
                self.model.queue_registry.require("gui").push(("status", "Takeoff aborted"))
            except Exception:
                pass
            return ReadySubState.READY_IDLE

        # 3) Fehler im MicroService → READY_IDLE
        if self._error:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", f"Takeoff FAILED: {self._error}")
                )
            except Exception:
                pass
            return ReadySubState.READY_IDLE

        # 4) Erfolg → READY_IDLE
        if self._done:
            try:
                self.model.queue_registry.require("gui").push(("status", "Takeoff complete"))
            except Exception:
                pass
            return ReadySubState.READY_IDLE

        # 5) Standard: im Takeoff bleiben
        return ReadySubState.READY_TAKEOFF
