# === PFAD-B FULL FILE: QGCR/communication/microservices/mission_upload_microservice.py ===

import time
from pymavlink import mavutil


class MissionUploadMicroService:
    """
    Event-getriebener, nicht-blockierender Mission-Upload.
    """

    STATE_IDLE = "IDLE"
    STATE_SEND_COUNT = "SEND_COUNT"
    STATE_WAIT_REQUEST = "WAIT_REQUEST"
    STATE_SEND_ITEM = "SEND_ITEM"
    STATE_WAIT_ACK = "WAIT_ACK"
    STATE_DONE = "DONE"
    STATE_ERROR = "ERROR"

    def __init__(self, connection, model, timeout=5.0):
        self.conn = connection
        self.model = model
        self.timeout = timeout

        self.started = False
        self.done = False
        self.error = None

        self._state = self.STATE_IDLE
        self._state_enter = 0.0

        self._mission = []
        self._expected_seq = 0
        self._last_request_seq = None
        self._ack_received = False

    # ------------------------------------------------------------
    # Dispatcher Hooks
    # ------------------------------------------------------------
    def on_mission_request_int(self, msg):
        self._last_request_seq = msg.seq

    def on_mission_ack(self, msg):
        self._ack_received = True

    # ------------------------------------------------------------
    # FSM API
    # ------------------------------------------------------------
    def start(self):
        self.started = True
        self.done = False
        self.error = None

        self._mission = list(self.model.mission.items)
        self._expected_seq = 0
        self._last_request_seq = None
        self._ack_received = False

        self._transition(self.STATE_SEND_COUNT)

    def tick(self):
        if not self.started or self.done or self.error:
            return

        now = time.time()

        if self._state == self.STATE_SEND_COUNT:
            self._do_send_count()

        elif self._state == self.STATE_WAIT_REQUEST:
            self._do_wait_request(now)

        elif self._state == self.STATE_SEND_ITEM:
            self._do_send_item()

        elif self._state == self.STATE_WAIT_ACK:
            self._do_wait_ack(now)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _transition(self, new):
        self._state = new
        self._state_enter = time.time()

    def _timeout(self, now):
        return (now - self._state_enter) >= self.timeout

    # ------------------------------------------------------------
    # States
    # ------------------------------------------------------------
    def _do_send_count(self):
        try:
            self.conn.master.mav.mission_count_send(
                1, 1, len(self._mission)
            )
        except Exception as e:
            self.error = f"MISSION_COUNT failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._transition(self.STATE_WAIT_REQUEST)

    def _do_wait_request(self, now):
        if self._last_request_seq is not None:
            if self._last_request_seq == self._expected_seq:
                self._transition(self.STATE_SEND_ITEM)
                return

        if self._timeout(now):
            self.error = "MISSION_REQUEST timeout"
            self._transition(self.STATE_ERROR)

    def _do_send_item(self):
        try:
            seq, cmd, x, y, z = self._mission[self._expected_seq]
            self.conn.master.mav.mission_item_int_send(
                1, 1,
                seq,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                cmd,
                0, 1,
                0, 0, 0, 0,
                int(x * 1e7),
                int(y * 1e7),
                float(z)
            )
        except Exception as e:
            self.error = f"MISSION_ITEM_INT failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._last_request_seq = None
        self._expected_seq += 1

        if self._expected_seq == len(self._mission):
            self._transition(self.STATE_WAIT_ACK)
        else:
            self._transition(self.STATE_WAIT_REQUEST)

    def _do_wait_ack(self, now):
        if self._ack_received:
            self.done = True
            self._transition(self.STATE_DONE)
            return

        if self._timeout(now):
            self.error = "MISSION_ACK timeout"
            self._transition(self.STATE_ERROR)
