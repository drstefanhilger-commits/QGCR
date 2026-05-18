# === PFAD-B FULL FILE: QGCR/states/main_state_map.py ===

from QGCR.states.main_state import MainState
from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.mission.mission_hfsm import MissionHFSM
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM

MAIN_STATE_MAP = {
    MainState.STARTUP: StartupHFSM,
    MainState.READY: ReadyHFSM,
    MainState.MISSION: MissionHFSM,
    MainState.AIRBORNE: AirborneHFSM,
}
