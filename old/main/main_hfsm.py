# === PFAD-B FULL FILE: QGCR/states/main_hfsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.main_state import MainState

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.mission.mission_hfsm import MissionHFSM
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM


class MainHFSM(BaseFSM):
    """
    High-Level FSM für das Gesamtsystem.
    - verwaltet StartupHFSM, ReadyHFSM, MissionHFSM, AirborneHFSM
    - entscheidet High-Level-Transitions ausschließlich in _on_exit()
    """

    def __init__(self, model):
        super().__init__(model, MainState.STARTUP)

        # Map der High-Level-States → HFSM-Klassen
        self.state_map = {
            MainState.STARTUP: StartupHFSM,
            MainState.READY: ReadyHFSM,
            MainState.MISSION: MissionHFSM,
            MainState.AIRBORNE: AirborneHFSM,
        }

        # High-Level-State (Pflicht für BaseFSM)
        self.active_state = MainState.STARTUP

        # Substate = High-Level-State selbst
        self.active_substate = MainState.STARTUP

        # Untergeordnete FSM
        self.active_fsm = None

        # Rückgabewert für _on_exit()
        self._next_state = MainState.STARTUP

    # ------------------------------------------------------------
    # SubFSM-Instanziierung
    # ------------------------------------------------------------
    def _create_subfsm_for_active_substate(self):
        fsm_class = self.state_map[self.active_substate]
        self.active_fsm = fsm_class(self.model)

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        self._create_subfsm_for_active_substate()

    def _on_during(self):
        next_state = self.active_fsm.on_update()

        if next_state is not None and next_state != self.active_substate:
            self.active_substate = next_state
            self.active_state = next_state  # <<< WICHTIG
            self._create_subfsm_for_active_substate()

    def _on_exit(self):
        return self.active_substate

    # ------------------------------------------------------------
    # Für GUI / Debug
    # ------------------------------------------------------------
    def get_state_dict(self):
        return {
            "state": str(self.active_state),
            "substate": str(self.active_substate),
            "active_fsm": type(self.active_fsm).__name__,
        }
