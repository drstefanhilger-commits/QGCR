# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_param_sync_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState


class StartupParamSyncFSM(BaseFSM):
    """
    STARTUP_PARAMS:
    - Führt einen nicht-blockierenden Parameter-Sync durch
    - Nutzt model.services.param_sync (MicroService)
    - Bei Erfolg → STARTUP_HOME
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_PARAMS)

        # KORREKT: param_sync (mit Unterstrich)
        self.ms = model.services.param_sync

        self._pending_event = None
        self._lost_heartbeat = False
        self._error = None
        self._done = False

    def _on_enter(self):
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
        self._done = True

    def _on_exit(self):

        if self._lost_heartbeat:
            return StartupSubState.STARTUP_HEARTBEAT

        if self._error:
            return StartupSubState.STARTUP_PARAMS

        if self._done:
            return StartupSubState.STARTUP_HOME

        return StartupSubState.STARTUP_PARAMS
