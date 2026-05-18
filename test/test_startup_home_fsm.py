from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup_substate import SubState
from QGCR.events.event import EventType


class StartupHomeFSM(BaseFSM):
    """
    Wartet auf PX4 Home-Position.
    """

    def __init__(self, model):
        super().__init__(model, SubState.STARTUP_HOME)
        self._next_state = SubState.STARTUP_HOME

    def _on_enter(self):
        if hasattr(self.model, "update_status"):
            self.model.update_status("Warte auf Home-Position...")

    def _on_during(self):
        # WICHTIG: next_state zu Beginn jedes Ticks zurücksetzen
        self._next_state = self.state_enum

        # Wenn Home bereits gesetzt → sofort weiter
        if self.model.home_set:
            self._next_state = SubState.STARTUP_OK
            return

        # Events aus Queue verarbeiten
        while not self.model.event_queue.empty():
            event = self.model.event_queue.get()

            if event.type == EventType.PX4_HOME_SET:
                self.model.home_set = True
                self._next_state = SubState.STARTUP_OK

    def _on_exit(self):
        return self._next_state

    def handle_event(self, event):
        """
        Test verlangt: home_set im Model setzen.
        """
        if event.type == EventType.PX4_HOME_SET:
            self.model.home_set = True

        return self.state_enum
