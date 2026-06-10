# === PFAD-B FULL FILE: QGCR/communication/microservices/takeoff_microservice.py ===

import time
from pymavlink import mavutil


class TakeoffMicroService:
    """
    Event-getriebener, nicht-blockierender Takeoff-Ablauf.
    """

    STATE_IDLE = "IDLE"
    STATE_ARMING = "ARMING"
    STATE_WAIT_ARMED = "WAIT_ARMED"
    STATE_SET_MODE = "SET_MODE"
    STATE_WAIT_MODE = "WAIT_MODE"
    STATE_SEND_TAKEOFF = "SEND_TAKEOFF"
    STATE_WAIT_CLIMB = "WAIT_CLIMB"
    STATE_DONE = "DONE"
    STATE_ERROR = "ERROR"

    def __init__(
        self,
        connection,
        model,
        target_altitude=10.0,
        arm_timeout=5.0,
        mode_timeout=5.0,
        takeoff_timeout=5.0,
        climb_timeout=20.0,
    ):
        self.conn = connection
        self.model = model

        self.target_altitude = float(target_altitude)

        self.arm_timeout = float(arm_timeout)
        self.mode_timeout = float(mode_timeout)
        self.takeoff_timeout = float(takeoff_timeout)
        self.climb_timeout = float(climb_timeout)

        self.started = False
        self.done = False
        self.error = None

        self._state = self.STATE_IDLE
        self._state_enter_time = 0.0

        self._armed = False
        self._last_mode = None
        self._last_relative_alt = None

    # ------------------------------------------------------------
    # Event-Callbacks
    # ------------------------------------------------------------
    def on_heartbeat(self, msg):
        try:
            self._armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
        except Exception:
            self._armed = False

        try:
            if hasattr(self.model, "px4_mode"):
                self._last_mode = self.model.px4_mode
        except Exception:
            pass

    def on_global_position_int(self, msg):
        try:
            self._last_relative_alt = msg.relative_alt / 1000.0
        except Exception:
            self._last_relative_alt = None

    # ------------------------------------------------------------
    # FSM API
    # ------------------------------------------------------------
    def start(self):
        self.started = True
        self.done = False
        self.error = None
        self._transition(self.STATE_ARMING)

    def tick(self):
        if not self.started or self.done or self.error:
            return

        now = time.time()

        if self._state == self.STATE_ARMING:
            self._do_state_arming(now)

        elif self._state == self.STATE_WAIT_ARMED:
            self._do_state_wait_armed(now)

        elif self._state == self.STATE_SET_MODE:
            self._do_state_set_mode(now)

        elif self._state == self.STATE_WAIT_MODE:
            self._do_state_wait_mode(now)

        elif self._state == self.STATE_SEND_TAKEOFF:
            self._do_state_send_takeoff(now)

        elif self._state == self.STATE_WAIT_CLIMB:
            self._do_state_wait_climb(now)

    # ------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------
    def _transition(self, new_state):
        self._state = new_state
        self._state_enter_time = time.time()

    def _timeout(self, now, limit):
        return (now - self._state_enter_time) >= limit

    # ------------------------------------------------------------
    # States
    # ------------------------------------------------------------
    def _do_state_arming(self, now):
        try:
            self._send_arm()
        except Exception as e:
            self.error = f"ARM send failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._transition(self.STATE_WAIT_ARMED)

    def _do_state_wait_armed(self, now):
        if self._armed:
            self._transition(self.STATE_SET_MODE)
            return

        if self._timeout(now, self.arm_timeout):
            self.error = "ARM timeout"
            self._transition(self.STATE_ERROR)

    def _do_state_set_mode(self, now):
        try:
            self._set_mode_takeoff()
        except Exception as e:
            self.error = f"Set mode failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._transition(self.STATE_WAIT_MODE)

    def _do_state_wait_mode(self, now):
        if self._last_mode and "TAKEOFF" in str(self._last_mode).upper():
            self._transition(self.STATE_SEND_TAKEOFF)
            return

        if self._timeout(now, self.mode_timeout):
            self._transition(self.STATE_SEND_TAKEOFF)

    def _do_state_send_takeoff(self, now):
        try:
            self._send_takeoff(self.target_altitude)
        except Exception as e:
            self.error = f"TAKEOFF send failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._transition(self.STATE_WAIT_CLIMB)

    def _do_state_wait_climb(self, now):
        if self._last_relative_alt is not None:
            if self._last_relative_alt >= max(0.5, 0.8 * self.target_altitude):
                self.done = True
                self._transition(self.STATE_DONE)
                return

        if self._timeout(now, self.climb_timeout):
            self.error = "Climb timeout"
            self._transition(self.STATE_ERROR)

    # ------------------------------------------------------------
    # MAVLink send
    # ------------------------------------------------------------
    def _send_arm(self):
        self.conn.master.mav.command_long_send(
            1, 1,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1, 0, 0, 0, 0, 0, 0
        )

    def _set_mode_takeoff(self):
        self.conn.master.set_mode("AUTO.TAKEOFF")

    def _send_takeoff(self, alt):
        self.conn.master.mav.command_long_send(
            1, 1,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, 0,
            0, 0,
            float(alt)
        )
