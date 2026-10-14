# === PFAD-B FULL FILE: QGCR/communication/microservices/parameter_sync_microservice.py ===

import time


class ParameterSyncMicroService:
    """
    Event-getriebener, nicht-blockierender Parameter-Sync (Download von PX4).
    - Sendet einmal PARAM_REQUEST_LIST
    - Erwartet viele PARAM_VALUE
    - Beendet, wenn alle empfangen sind
    """

    STATE_IDLE = "IDLE"
    STATE_REQUEST_LIST = "REQUEST_LIST"
    STATE_WAIT_VALUES = "WAIT_VALUES"
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
        self._received_count = 0

    # ------------------------------------------------------------
    # Dispatcher Hook
    # ------------------------------------------------------------
    def on_param_value(self, msg):
        """
        Wird vom Dispatcher oder Harness aufgerufen, wenn ein PARAM_VALUE eintrifft.
        """
        try:
            name = msg.param_id
            value = msg.param_value
            index = msg.param_index
            count = msg.param_count
        except Exception:
            return

        if self._expected_count is None:
            self._expected_count = count

        if not hasattr(self.model, "params"):
            self.model.params = {}

        self.model.params[name] = (value, index)

        self._received_count += 1

    # ------------------------------------------------------------
    # FSM API
    # ------------------------------------------------------------
    def start(self):
        self.started = True
        self.done = False
        self.error = None

        self._expected_count = None
        self._received_count = 0

        if hasattr(self.model, "params"):
            self.model.params.clear()
        else:
            self.model.params = {}

        self._transition(self.STATE_REQUEST_LIST)

    def tick(self):
        if not self.started or self.done or self.error:
            return

        now = time.time()

        if self._state == self.STATE_REQUEST_LIST:
            self._do_request_list()

        elif self._state == self.STATE_WAIT_VALUES:
            self._do_wait_values(now)

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
            # Standard: System 1, Component 1
            self.conn.master.mav.param_request_list_send(1, 1)
        except Exception as e:
            self.error = f"PARAM_REQUEST_LIST failed: {e}"
            self._transition(self.STATE_ERROR)
            return

        self._transition(self.STATE_WAIT_VALUES)

    def _do_wait_values(self, now):
        if self._expected_count is not None and self._received_count >= self._expected_count:
            self.done = True
            self._transition(self.STATE_DONE)
            return

        if self._timeout(now):
            self.error = "PARAM_VALUE timeout"
            self._transition(self.STATE_ERROR)
