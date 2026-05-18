# === PFAD-B FULL FILE: QGCR/states/airborne/airborne_state_map.py ===

from QGCR.states.airborne.airborne_substate import AirborneSubState
from QGCR.states.airborne.subfsms.airborne_takeoff_fsm import AirborneTakeoffFSM
from QGCR.states.airborne.subfsms.airborne_mission_fsm import AirborneMissionFSM
from QGCR.states.airborne.subfsms.airborne_hold_fsm import AirborneHoldFSM
from QGCR.states.airborne.subfsms.airborne_lost_fsm import AirborneLostFSM
from QGCR.states.airborne.subfsms.airborne_exit_fsm import AirborneExitFSM

AIRBORNE_STATE_MAP = {
    AirborneSubState.AIRBORNE_TAKEOFF: AirborneTakeoffFSM,
    AirborneSubState.AIRBORNE_MISSION: AirborneMissionFSM,
    AirborneSubState.AIRBORNE_HOLD:    AirborneHoldFSM,
    AirborneSubState.AIRBORNE_LOST:    AirborneLostFSM,
    AirborneSubState.AIRBORNE_EXIT:    AirborneExitFSM,
}
