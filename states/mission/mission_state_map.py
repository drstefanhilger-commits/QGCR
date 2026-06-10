from QGCR.states.mission.mission_substate import MissionSubState

from QGCR.states.mission.subfsms.mission_idle_fsm import MissionIdleFSM
from QGCR.states.mission.subfsms.mission_upload_fsm import MissionUploadFSM
from QGCR.states.mission.subfsms.mission_download_fsm import MissionDownloadFSM


MISSION_STATE_MAP = {
    MissionSubState.MISSION_IDLE: MissionIdleFSM,
    MissionSubState.MISSION_UPLOAD: MissionUploadFSM,
    MissionSubState.MISSION_DOWNLOAD: MissionDownloadFSM,
}
