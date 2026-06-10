# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_params_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState

class StartupParamsFSM(BaseFSM):
    """
    Vereinfachter PARAMS-SubFSM:
    - Loggt den Eintritt
    - (optional) könnte später Param-Sync triggern
    - schaltet deterministisch weiter zu STARTUP_HOME
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_PARAMS)
        self._next_state = StartupSubState.STARTUP_HOME

    def _on_enter(self):
        super()._on_enter()
        self.model.log.qgcr("[STARTUP_PARAMS] ENTER (no param sync, direct → HOME)")

    def _on_during(self):
        # Kein echtes Param-Loading, wir gehen direkt weiter.
        pass

    def _on_exit(self):
        self.model.log.qgcr("[STARTUP_PARAMS] EXIT → STARTUP_HOME")
        return self._next_state
