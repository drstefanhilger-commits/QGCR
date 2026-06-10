# === PFAD-B FULL FILE: QGCR/states/ready/subfsms/ready_mission_start_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState

class ReadyMissionStartFSM(BaseFSM):
    """
    Startet eine Mission aus dem READY-HFSM heraus.
    - sendet MAV_CMD_MISSION_START
    - setzt next_state = READY_IDLE
    """

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_MISSION_START)
        self._next_state = ReadySubState.READY_IDLE
        self._sent = False

    def _on_enter(self):
        super()._on_enter()
        self.model.log.qgcr("[READY_MISSION_START] ENTER")

        try:
            # MAV_CMD_MISSION_START
            self.model.connection.master.mav.command_long_send(
                self.model.target_system,
                self.model.target_component,
                300,  # MAV_CMD_MISSION_START
                0,
                0, 0, 0, 0, 0, 0, 0
            )
            self._sent = True
            self.model.log.qgcr("[READY_MISSION_START] Mission start command sent")
        except Exception as e:
            self.model.log.qgcr(f"[READY_MISSION_START] ERROR sending mission start: {e}")

    def _on_during(self):
        pass

    def _on_exit(self):
        self.model.log.qgcr("[READY_MISSION_START] EXIT → READY_IDLE")
        return self._next_state
