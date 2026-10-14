# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_ok_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState

class StartupOkFSM(BaseFSM):
    """
    Letzter Zustand der Startup-Pipeline.
    Signalisiert dem StartupHFSM, dass nach READY gewechselt werden soll.
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_OK)
        self._next_state = StartupSubState.STARTUP_OK
        self._sent = False

    def _on_enter(self):
        super()._on_enter()
        self.model.log.qgcr("[STARTUP_OK] ENTER")

        # Einmaliges Event an HFSM schicken: gehe nach READY
        if not self._sent:
            self.model.hfsm_events.append("EV_GOTO_READY")
            self._sent = True
            self.model.log.qgcr("[STARTUP_OK] EV_GOTO_READY queued")

    def _on_during(self):
        pass

    def _on_exit(self):
        self.model.log.qgcr("[STARTUP_OK] EXIT")
        return self._next_state
