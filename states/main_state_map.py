# === PFAD-B FULL FILE: QGCR/states/main_state_map.py ===

from QGCR.states.main_state import MainState

# High-Level HFSMs
from QGCR.states.setup.setup_hfsm import SetupHFSM 
from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.mission.mission_hfsm import MissionHFSM
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM
from QGCR.states.reset.reset_hfsm import ResetHFSM
from QGCR.states.lost.lost_hfsm import LostHFSM


MAIN_STATE_MAP = {
    MainState.SETUP: SetupHFSM,
    MainState.STARTUP: StartupHFSM,
    MainState.READY: ReadyHFSM,
    MainState.MISSION: MissionHFSM,
    MainState.AIRBORNE: AirborneHFSM,
    MainState.RESET: ResetHFSM,
    MainState.LOST: LostHFSM,
}
