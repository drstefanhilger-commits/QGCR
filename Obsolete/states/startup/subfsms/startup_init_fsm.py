# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_init_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState

class StartupInitFSM(BaseFSM):
    """
    Erster Zustand der Startup-Pipeline.
    Macht nichts außer sofort weiterzuschalten zu STARTUP_HEARTBEAT.
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_INIT)
        self._next_state = StartupSubState.STARTUP_HEARTBEAT

    def _on_enter(self):
        super()._on_enter()
        self.model.log.qgcr("[STARTUP_INIT] ENTER")

    def _on_during(self):
        pass

    def _on_exit(self):
        self.model.log.qgcr("[STARTUP_INIT] EXIT → STARTUP_HEARTBEAT")
        return self._next_state
