# === PFAD-B FULL FILE: QGCR/states/setup/setup_hfsm.py ===

from QGCR.states.base_hfsm import BaseHFSM
from QGCR.states.main_state import MainState


class SetupHFSM(BaseHFSM):
    """
    Minimaler SETUP-HFSM:
    - Wird nach RESET betreten
    - Wartet auf ein AIM/SETUP_DONE Event
    - Übergang nach STARTUP
    """

    def __init__(self, model):
        super().__init__(model, MainState.SETUP)
        self._next_state = MainState.SETUP

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def _on_enter(self):
        self.model.hfsm_main = "SETUP"
        self.model.hfsm_sub = "WAITING"
        self.model.push_state_update()

        # Falls später Wiederholungen aktiv sind:
        # (hier nur Platzhalter, noch nicht implementiert)
        if hasattr(self.model, "scenario"):
            if getattr(self.model.scenario, "skip_setup", False):
                self._next_state = MainState.STARTUP

    # ------------------------------------------------------------
    # DURING
    # ------------------------------------------------------------
    def _on_during(self):

        # GUI-Button "AIM" → Event "AIM"
        if self._pop_event("AIM"):
            self._next_state = MainState.STARTUP
            return

        # Alternativ generisches Event
        if self._pop_event("HFSM_EVENT_SETUP_DONE"):
            self._next_state = MainState.STARTUP
            return

        # RESET führt wieder nach SETUP
        if self._pop_event("RESET"):
            self._next_state = MainState.SETUP
            return

    # ------------------------------------------------------------
    # EXIT
    # ------------------------------------------------------------
    def _on_exit(self):
        return self._next_state
