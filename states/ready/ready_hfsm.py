# === PFAD-B FULL FILE: QGCR/states/ready/ready_hfsm.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM
import time


class ReadyHFSM(BaseHFSM):

    def __init__(self, model):
        super().__init__(model, MainState.READY)
        self._next_state = MainState.READY
        self._enter_time = 0.0

    def _on_enter(self):
        self.model.log.qgcr("[ReadyHFSM] entering READY")
        self.model.hfsm_main = "READY"
        self.model.hfsm_sub = "IDLE"
        self.model.push_state_update()

        # Zeit merken für Grace-Phase
        self._enter_time = time.time()

        # 🔥 WICHTIG: alte Events verwerfen (z.B. TAKEOFF vom vorherigen Zyklus)
        try:
            self.model.hfsm_events.clear()
            self.model.log.qgcr("[ReadyHFSM] cleared hfsm_events on enter")
        except Exception:
            pass

    def _on_during(self):
        self.model.takeoff.tick()

        if self.model.hfsm_events:
            event = self.model.hfsm_events.popleft()

            if event == "TAKEOFF":
                self._next_state = MainState.AIRBORNE
                return

            if event == "RESET":
                self.model.log.qgcr("[ReadyHFSM] RESET received")
                self._next_state = MainState.RESET
                return

        # Grace-Phase nach Startup/Reset
        if time.time() - self._enter_time < 5.0:
            self._next_state = MainState.READY
            return

        if not self.model.connection_ready():
            self.model.log.qgcr("[ReadyHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        self._next_state = MainState.READY

    def _on_exit(self):
        return self._next_state
