# === PFAD-B FULL FILE: QGCR/communication/microservices/mission_download_microservice.py ===

import time
from pymavlink import mavutil


class MissionDownloadMicroService:
    """
    Event-getriebener, nicht-blockierender Mission-Download.
    """

    STATE_IDLE = "IDLE"
    STATE_REQUEST_LIST = "REQUEST_LIST"
    STATE_WAIT_COUNT = "WAIT_COUNT"
    STATE_REQUEST_ITEM = "REQUEST_ITEM"
    STATE_WAIT_ITEM = "WAIT_ITEM"
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

        self._expected_count = None
        self._received_items = {}
        self._expected_seq = 0

        self._count_received = False
        self._last_item_msg = None

    # ------------------------------------------------------------
    # Dispatcher Hooks
    # ------------------------------------------------------------
    def on_mission_count(self, msg):
        self._expected_count = msg.count
        self._count_received = True

    def on_mission_item_int(self, msg):
        self._last_item_msg = msg

    # ------------------------------------------------------------
    # FSM API
    # ------------------------------------------------------------
    def start(self):
        self.started = True
        self.done = False
        self.error = None

        self._expected_count = None
        self._received_items = {}
        self._expected_seq = 0
        self._count_received = False
        self._last_item_msg = None

        self._transition(self.STATE_REQUEST_LIST)

    def tick(self):
        if not self.started or self.done or self.error:
            return

        now = time.time()

        if self._state == self.STATE_REQUEST_LIST:
            self._do_request_list()

        elif self._state == self.STATE_WAIT_COUNT:
            self._do_wait_count(now)

        elif self._state == self.STATE_REQUEST_ITEM:
            self._do_request_item()

        elif self._state == self.STATE_WAIT_ITEM:
            self._do_wait_item(now)

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
    def _do_request_list(self):
        try:
            self.conn.master.mav.mission_request_list_send(
                self.conn.master.target_system,
                self.conn.master.target_component,
            )
        except Exception as e:
            self.error = f"REQUEST_LIST failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._transition(self.STATE_WAIT_COUNT)

    def _do_wait_count(self, now):
        if self._count_received:
            self._transition(self.STATE_REQUEST_ITEM)
            return

        if self._timeout(now):
            self.error = "MISSION_COUNT timeout"
            self._transition(self.STATE_ERROR)

    def _do_request_item(self):
        try:
            self.conn.master.mav.mission_request_int_send(
                self.conn.master.target_system,
                self.conn.master.target_component,
                self._expected_seq,
            )
        except Exception as e:
            self.error = f"REQUEST_ITEM failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._transition(self.STATE_WAIT_ITEM)

    def _do_wait_item(self, now):
        if self._last_item_msg is not None:
            msg = self._last_item_msg
            self._last_item_msg = None

            self._received_items[msg.seq] = msg

            self._expected_seq += 1

            if self._expected_seq == self._expected_count:
                self.done = True
                self._transition(self.STATE_DONE)
            else:
                self._transition(self.STATE_REQUEST_ITEM)

            return

        if self._timeout(now):
            self.error = "MISSION_ITEM timeout"
            self._transition(self.STATE_ERROR)
