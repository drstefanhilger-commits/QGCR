import time
from pymavlink import mavutil

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState


class ReadyResetFSM(BaseFSM):
    """
    RESET:
    - Bricht Flug ab (HOLD, falls armed)
    - Disarmt (falls armed)
    - Setzt Model-State zurück
    - Geht zurück in READY_IDLE
    """

    TIMEOUT = 3.0

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_RESET)
        self._next_state = ReadySubState.READY_RESET
        self.start_time = 0.0
        self.phase = "INIT"

    def _on_enter(self):
        self.start_time = time.time()
        self.phase = "INIT"
        self.model.log.qgcr("[READY_RESET] ENTER")

    def _on_during(self):
        now = time.time()

        # Timeout
        if now - self.start_time > self.TIMEOUT:
            self.model.log.qgcr("[READY_RESET] Timeout → FORCE READY")
            self._force_ready()
            return

        # INIT → HOLD (falls armed)
        if self.phase == "INIT":
            if getattr(self.model, "px4_armed", False):
                self._send_hold()
                self.phase = "WAIT_HOLD"
                self.start_time = now
                return
            else:
                self.phase = "SEND_DISARM"
                return

        # WAIT_HOLD
        if self.phase == "WAIT_HOLD":
            self.phase = "SEND_DISARM"
            return

        # SEND_DISARM
        if self.phase == "SEND_DISARM":
            if getattr(self.model, "px4_armed", False):
                self._send_disarm()
                self.phase = "WAIT_DISARM"
                self.start_time = now
                return
            else:
                self.phase = "RESET_MODEL"
                return

        # WAIT_DISARM
        if self.phase == "WAIT_DISARM":
            if not getattr(self.model, "px4_armed", False):
                self.phase = "RESET_MODEL"
                return
            return

        # RESET_MODEL
        if self.phase == "RESET_MODEL":
            self._reset_model_state()
            self.phase = "DONE"
            return

        # DONE → READY_IDLE
        if self.phase == "DONE":
            self.model.log.qgcr("[READY_RESET] DONE → READY_IDLE")
            self._next_state = ReadySubState.READY_IDLE
            return

    def _on_exit(self):
        return self._next_state

    # ------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------
    def _send_hold(self):
        self.model.log.qgcr("[READY_RESET] SEND HOLD")
        try:
            if self.model.connection and self.model.connection.master:
                self.model.connection.master.set_mode("HOLD")
            else:
                self.model.log.qgcr("[READY_RESET] HOLD skipped (no connection)")
        except Exception as e:
            self.model.log.qgcr(f"[READY_RESET] HOLD failed: {e}")

    def _send_disarm(self):
        self.model.log.qgcr("[READY_RESET] SEND DISARM")
        try:
            if self.model.connection and self.model.connection.master:
                self.model.connection.master.mav.command_long_send(
                    self.model.connection.master.target_system,
                    1,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,
                    0, 0, 0, 0, 0, 0, 0
                )
            else:
                self.model.log.qgcr("[READY_RESET] DISARM skipped (no connection)")
        except Exception as e:
            self.model.log.qgcr(f"[READY_RESET] DISARM failed: {e}")

    def _reset_model_state(self):
        self.model.log.qgcr("[READY_RESET] CLEAR MODEL STATE")
        self.model.vehicle_lat = None
        self.model.vehicle_lon = None
        self.model.vehicle_alt = None
        self.model.px4_armed = False
        self.model.mission_running = False
        self.model.mission_loaded = False

    def _force_ready(self):
        self.model.log.qgcr("[READY_RESET] FORCE READY")
        self._reset_model_state()
        self._next_state = ReadySubState.READY_IDLE
