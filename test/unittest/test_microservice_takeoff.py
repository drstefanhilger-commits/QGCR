# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_param_sync_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState


class StartupParamSyncFSM(BaseFSM):
    """
    STARTUP_PARAMS:
    - Führt einen nicht-blockierenden Parameter-Sync durch
    - Nutzt model.services.param_sync (MicroService)
    - Bei Erfolg → STARTUP_HOME
    - Bei Fehler → bleibt in STARTUP_PARAMS (oder optional Fehlerzustand)
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_PARAMS)

        # ParamSync MicroService (KORRIGIERT)
        self.ms = model.services.param_sync

        # Event-/Status-Puffer
        self._pending_event = None
        self._lost_heartbeat = False
        self._error = None
        self._done = False

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        """
        ParamSync starten.
        """
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Startup: Parameter-Sync gestartet")
            )
        except Exception:
            pass

        self._pending_event = None
        self._lost_heartbeat = False
        self._error = None
        self._done = False

        self.ms.start()

    def _on_during(self):
        """
        LEERER ParamSync – sofort weiter zu STARTUP_HOME.
        """
        self._done = True

    def _on_exit(self):
        """
        EINZIGER Ort für Sub-State-Wechsel.
        """

        if self._lost_heartbeat:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", "Parameter-Sync abgebrochen: Heartbeat verloren")
                )
            except Exception:
                pass
            return StartupSubState.STARTUP_HEARTBEAT

        if self._error:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", f"Parameter-Sync FEHLER: {self._error}")
                )
            except Exception:
                pass
            return StartupSubState.STARTUP_PARAMS

        if self._done:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", "Parameter-Sync abgeschlossen")
                )
            except Exception:
                pass
            return StartupSubState.STARTUP_HOME

        return StartupSubState.STARTUP_PARAMS
