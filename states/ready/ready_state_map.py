# === PFAD-B FULL FILE: QGCR/states/ready/ready_state_map.py ===

"""
State Map für die READY-SubFSMs.

WICHTIG:
READY verwaltet ausschließlich Boden-/Bereitschaftsverhalten.
Mission-Operationen gehören NICHT in den READY-Zustand.

Enthaltene SubFSMs:
    * READY_IDLE
    * READY_TAKEOFF
    * READY_HEARTBEAT_LOST
    * READY_MISSION
"""

from QGCR.states.ready.ready_substate import ReadySubState
# SubFSMs
from QGCR.states.ready.subfsms.ready_idle_fsm import ReadyIdleFSM
from QGCR.states.ready.subfsms.ready_takeoff_fsm import ReadyTakeoffFSM
from QGCR.states.ready.subfsms.ready_heartbeat_lost_fsm import ReadyHeartbeatLostFSM
from .subfsms.ready_mission_fsm import ReadyMissionFSM


READY_STATE_MAP = {
    ReadySubState.READY_IDLE: ReadyIdleFSM,
    ReadySubState.READY_TAKEOFF: ReadyTakeoffFSM,
    ReadySubState.READY_HEARTBEAT_LOST: ReadyHeartbeatLostFSM,
    ReadySubState.READY_MISSION: ReadyMissionFSM,
}
