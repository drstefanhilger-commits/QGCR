# === PFAD-B FULL FILE: QGCR/states/mission/mission_hfsm.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM


class MissionHFSM(BaseHFSM):

    def __init__(self, model):
        super().__init__(model, MainState.MISSION)
        self._next_state = MainState.MISSION

    def _on_enter(self):
        self.model.log.qgcr("[MissionHFSM] entering MISSION")
        self.model.hfsm_main = "MISSION"
        self.model.hfsm_sub = "IDLE"
        self.model.push_state_update()

    def _on_during(self):
        if self.model.hfsm_events:
            event = self.model.hfsm_events.popleft()

            match event:
                case "BACK" | "MISSION_BACK" | "EV_GOTO_READY":
                    self.model.log.qgcr(f"[MissionHFSM] {event} → READY")
                    self._next_state = MainState.READY
                    return

                case "RESET":
                    self.model.log.qgcr("[MissionHFSM] RESET received")
                    self._next_state = MainState.RESET
                    return

        if not self.model.connection_ready():
            self.model.log.qgcr("[MissionHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        self._next_state = MainState.MISSION

    def _on_exit(self):
        return self._next_state
