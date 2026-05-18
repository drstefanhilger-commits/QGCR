# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_ok_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState


class StartupOkFSM(BaseFSM):
    """
    STARTUP_OK:
    - Letzter Schritt der Startup-Pipeline
    - Signalisiert, dass alle Startup-Checks abgeschlossen sind
    - Übergang zu READY erfolgt in StartupHFSM._on_exit()
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_OK)

        # Event-/Status-Puffer
        self._pending_event = None
        self._lost_heartbeat = False

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        """
        GUI informieren, dass Startup abgeschlossen ist.
        """
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Startup abgeschlossen – System bereit")
            )
        except Exception:
            pass

        try:
            self.model.queue_registry.require("gui").push(
                ("log", "Startup OK – Übergabe an READY")
            )
        except Exception:
            pass

        # Reset Flags
        self._pending_event = None
        self._lost_heartbeat = False

    def _on_during(self):
        """
        Keine Aktionen – aber wir prüfen Heartbeat und lesen Events.
        """

        # Heartbeat verloren?
        if not self.model.px4_connected:
            self._lost_heartbeat = True
            return

        # GUI-Events lesen (werden ignoriert)
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

        # KEINE Statewechsel hier!

    def _on_exit(self):
        """
        EINZIGER Ort für Sub-State-Wechsel.
        """

        # 1) Heartbeat verloren → zurück zu STARTUP_HEARTBEAT
        if self._lost_heartbeat:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", "Startup OK abgebrochen (Heartbeat verloren)")
                )
            except Exception:
                pass
            return StartupSubState.STARTUP_HEARTBEAT

        # 2) Standard: in STARTUP_OK bleiben
        return StartupSubState.STARTUP_OK
