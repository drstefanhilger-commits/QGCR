# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_heartbeat_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState


class StartupHeartbeatFSM(BaseFSM):
    """
    Wartet auf den ersten echten PX4-Heartbeat.
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_HEARTBEAT)

        # interner Zustand
        self._pending_event = None

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        # Nur GUI-Status anzeigen – KEIN Heartbeat-Event erzeugen!
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Startup: Waiting for PX4 heartbeat")
            )
        except Exception:
            pass

    def _on_during(self):
        """
        Prüft, ob ein echter Heartbeat empfangen wurde.
        KEINE Statewechsel hier.
        """

        # GUI-Events lesen (falls später relevant)
        self._pending_event = None
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

        # Keine Statewechsel hier!
        pass

    def _on_exit(self):
        """
        EINZIGER Ort für Sub-State-Wechsel.
        """

        # 1) Kein echter Heartbeat → im Heartbeat-Substate bleiben
        if not self.model.px4_connected or self.model.px4_heartbeat_count == 0:
            return StartupSubState.STARTUP_HEARTBEAT

        # 2) ECHTER Heartbeat empfangen → weiter zu PARAMSYNC
        return StartupSubState.STARTUP_PARAMS
