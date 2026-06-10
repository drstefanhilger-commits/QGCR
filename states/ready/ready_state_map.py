# === PFAD-B FULL FILE: QGCR/states/ready/ready_state_map.py ===

from QGCR.states.ready.ready_substate import ReadySubState

# SubFSMs
from QGCR.states.ready.subfsms.ready_idle_fsm import ReadyIdleFSM
from QGCR.states.ready.subfsms.ready_takeoff_fsm import ReadyTakeoffFSM
from QGCR.states.ready.subfsms.ready_land_fsm import ReadyLandFSM
from QGCR.states.ready.subfsms.ready_stop_fsm import ReadyStopFSM
from QGCR.states.ready.subfsms.ready_mission_start_fsm import ReadyMissionStartFSM
from QGCR.states.ready.subfsms.ready_reset_fsm import ReadyResetFSM


READY_STATE_MAP = {
    ReadySubState.READY_IDLE: ReadyIdleFSM,
    ReadySubState.READY_TAKEOFF: ReadyTakeoffFSM,
    ReadySubState.READY_LAND: ReadyLandFSM,
    ReadySubState.READY_STOP: ReadyStopFSM,
    ReadySubState.READY_MISSION_START: ReadyMissionStartFSM,
    ReadySubState.READY_RESET: ReadyResetFSM,
}
