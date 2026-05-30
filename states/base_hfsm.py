# === PFAD-B FULL FILE: QGCR/states/base_hfsm.py ===

from QGCR.states.base import Base

class BaseHFSM(Base):
    """
    Gemeinsame Basis für alle High-Level-FSMs (STARTUP, READY, MISSION, AIRBORNE).
    - Setzt model.hfsm_main beim Betreten
    - Aktualisiert model.hfsm_main beim Verlassen
    - SubFSMs erben NICHT hiervon
    """

    def __init__(self, model, main_state):
        super().__init__(model, main_state)
        self.main_state = main_state

    def _on_enter(self):
        """
        High-Level-State wurde betreten.
        """
        self.model.hfsm_main = self.main_state.name
        self.model.push_state_update()

    def _on_during(self):
        pass

    def _on_exit(self):
        """
        Wird von Kindklassen überschrieben.
        Aktualisiert den MainState im Model.
        """
        return self._next_state