from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState as SubState
from QGCR.events.event import EventType


class StartupParamSyncFSM(BaseFSM):
    """
    Wartet auf PX4 Parameter-Sync.
    """

    def __init__(self, model):
        super().__init__(model, SubState.STARTUP_PARAMS)
        self._next_state = SubState.STARTUP_PARAMS

    def _on_enter(self):
        if hasattr(self.model, "update_status"):
            self.model.update_status("Parameter werden synchronisiert...")

    def _on_during(self):
        # WICHTIG: next_state zu Beginn jedes Ticks zurücksetzen
        self._next_state = self.state_enum

        while not self.model.event_queue.empty():
            event = self.model.event_queue.get()

            if event.type == EventType.PX4_PARAMS_RECEIVED:
                self.model.params_received = True

            elif event.type == EventType.PX4_PARAMS_SYNCED:
                self.model.params_synced = True
                self._next_state = SubState.STARTUP_HOME

    def _on_exit(self):
        return self._next_state

    def handle_event(self, event):
        """
        Test verlangt: Flags im Model setzen.
        """
        if event.type == EventType.PX4_PARAMS_RECEIVED:
            self.model.params_received = True

        elif event.type == EventType.PX4_PARAMS_SYNCED:
            self.model.params_synced = True

        return self.state_enum
