# === PFAD-B FULL FILE: QGCR/states/base_fsm.py ===

from QGCR.states.base import Base

class BaseFSM(Base):
    """
    #     Basis-FSM mit sauberem Lifecycle:
    #     - _on_enter() wird genau einmal beim Eintritt ausgeführt
    #     - _on_during() sammelt Infos, tickt Microservices, KEINE Statewechsel
    #     - _on_exit() entscheidet deterministisch den nächsten Zustand
    #     - on_update() führt den gesamten Lifecycle aus und liefert next_state zurück
    """

    def __init__(self, model, state_enum):
        super().__init__(model, state_enum)
        self.state_enum =   state_enum

    def _on_enter(self):
        """
        State wurde betreten.
        """
        self.model.hfsm_sub = self.state_enum.name
        self.model.push_state_update()

    def _on_during(self):
        pass

    def _on_exit(self):
        """
        Wird von Kindklassen überschrieben.
        """
        return self._next_state
