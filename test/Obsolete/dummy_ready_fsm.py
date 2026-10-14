from QGCR.states.base_fsm import BaseFSM
from QGCR.states.main_state import MainState


class DummyReadyFSM(BaseFSM):
    """
    Minimaler READY-FSM für den Harness-Test.
    Macht nichts außer stabil READY zurückzugeben.
    """

    def __init__(self, model):
        super().__init__(model, MainState.READY)

    def _on_enter(self):
        pass

    def _on_during(self):
        pass

    def _on_exit(self):
        return MainState.READY
