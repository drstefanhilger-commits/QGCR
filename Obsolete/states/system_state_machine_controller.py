from QGCR.states.base_machine_controller import BaseMachineController
from QGCR.states.main_state import MainState

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.mission.mission_hfsm import MissionHFSM
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM
from QGCR.states.startup.startup_substate_machine_controller import StartupSubStateMachineController

class MainStateMachineController(BaseMachineController):
    """
    High-Level Controller für die vier HFSMs:
    - StartupHFSM
    - ReadyHFSM
    - MissionHFSM
    - AirborneHFSM
    """

    def __init__(self, model):
        super().__init__(model)
        self.main_state = MainState
        self.subcontroller = StartupSubStateMachineController(self.model)
        model.controller = self
        self.build_states()
        self.current_state = MainState.STARTUP   # <<< WICHTIG


    def build_states(self):
        self.state_map = {
            MainState.STARTUP: StartupHFSM(self.model),
            MainState.READY: ReadyHFSM(self.model),
            MainState.MISSION: MissionHFSM(self.model),
            MainState.AIRBORNE: AirborneHFSM(self.model),
        }

    def handle_takeoff(self):
        # Event an READY-HFSM weiterreichen
        if self.current_state == MainState.READY:
            self.state_map[MainState.READY].on_takeoff()
