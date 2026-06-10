from QGCR.model.model import Model
from QGCR.states.main_state import MainState
from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.test.dummy_ready_fsm import DummyReadyFSM


class MockStartupController:
    """
    Minimaler Controller nur für den Startup-HFSM-Harness-Test.
    """

    def __init__(self):
        self.model = Model()
        self.state_map = {
            MainState.STARTUP: StartupHFSM(self.model),
            MainState.READY:   DummyReadyFSM(self.model)
        }
        self.current_state = MainState.STARTUP

        # Direkter Zugriff auf Sub-FSMs
        self.sub = self.state_map[self.current_state].sub

    def process_event(self, event):
        """
        Events werden in die model.event_queue gelegt.
        """
        self.model.event_queue.put(event)

    def step(self):
        """
        Einen Tick ausführen.
        """
        state_obj = self.state_map[self.current_state]
        next_state = state_obj.on_update()
        self.current_state = next_state
        return next_state
