# === PFAD-B FULL FILE: QGCR/states/startup/startup_state_map.py ===

from QGCR.states.startup.startup_substate import StartupSubState

from QGCR.states.startup.subfsms.startup_init_fsm import StartupInitFSM
from QGCR.states.startup.subfsms.startup_heartbeat_fsm import StartupHeartbeatFSM
from QGCR.states.startup.subfsms.startup_params_fsm import StartupParamsFSM
from QGCR.states.startup.subfsms.startup_home_fsm import StartupHomeFSM
from QGCR.states.startup.subfsms.startup_mission_fsm import StartupMissionFSM
from QGCR.states.startup.subfsms.startup_ok_fsm import StartupOkFSM

STARTUP_STATE_MAP = {
    StartupSubState.STARTUP_INIT: StartupInitFSM,
    StartupSubState.STARTUP_HEARTBEAT: StartupHeartbeatFSM,
    StartupSubState.STARTUP_PARAMS: StartupParamsFSM,
    StartupSubState.STARTUP_HOME: StartupHomeFSM,
    StartupSubState.STARTUP_MISSION: StartupMissionFSM,
    StartupSubState.STARTUP_OK: StartupOkFSM,
}
