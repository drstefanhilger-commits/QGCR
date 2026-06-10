# === PFAD-B FULL FILE: QGCR/states/airborne/airborne_hfsm.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM


class AirborneHFSM(BaseHFSM):

    def __init__(self, model):
        super().__init__(model, MainState.AIRBORNE)
        self._next_state = MainState.AIRBORNE
        
    def _on_enter(self):
        self.model.log.qgcr("[AirborneHFSM] entering AIRBORNE")
        self.model.hfsm_main = "AIRBORNE"
        self.model.hfsm_sub = "FLIGHT"
        self.model.push_state_update()
        if self.model.takeoff.state == self.model.takeoff.STATE_IDLE:
            self.model.takeoff.start()
            self.model.log.qgcr("[AirborneHFSM] TAKEOFF Microservice started")

    def _on_during(self):
        # print("[HFSM DEBUG] AirborneHFSM tick")
        # print("[HFSM DEBUG] Events:", list(self.model.hfsm_events))

        self.model.takeoff.tick()

        if self.model.hfsm_events:
            event = self.model.hfsm_events.popleft()

            if event == "RESET":
                self.model.log.qgcr("[AirborneHFSM] RESET received")
                self._next_state = MainState.RESET
                return

        if not self.model.connection_ready():
            self.model.log.qgcr("[AirborneHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        self._next_state = MainState.AIRBORNE

    def _on_exit(self):
        return self._next_state
