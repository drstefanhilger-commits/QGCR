# === PFAD-B FULL FILE: lost_hfsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.main_state import MainState


class LostHFSM(BaseFSM):
    """
    Minimaler LOST-HFSM.
    Bleibt im LOST-State, bis spätere Logik implementiert wird.
    """

    def __init__(self, model):
        super().__init__(model, MainState.LOST)
        self._next_state = MainState.LOST

    def _on_enter(self):
        # LOST hat aktuell keine Enter-Logik
        pass

    def _on_during(self):
        # LOST bleibt LOST, bis echte Recovery-Logik kommt
        self._next_state = MainState.LOST

    def _on_exit(self):
        return self._next_state

    def handle_event(self, event):
        # LOST ignoriert Events (vorerst)
        return self.state_enum
