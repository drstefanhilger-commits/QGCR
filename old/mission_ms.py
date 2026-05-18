# === PFAD-B FULL FILE: QGCR/microservices/mission_ms.py ===

import time
from pymavlink import mavutil


class MissionMicroService:
    """
    MicroService für Mission Download + Upload.
    Implementiert eine kleine deterministische FSM:

        IDLE
        REQUEST_COUNT
        WAIT_COUNT
        REQUEST_ITEMS
        WAIT_ITEMS
        DONE
        ERROR

    - Keine Blockaden
    - Keine Busy-Loops
    - Tick() wird vom MicroServiceController aufgerufen
    """

    TIMEOUT = 5.0

    def __init__(self, model, connection):
        self.model = model
        self.connection = connection

        # FSM
        self.state = "IDLE"
        self.start_time = 0.0

        # Download
        self.expected_count = 0
        self.received_items = 0

        # Upload
        self.upload_items = None
        self.upload_index = 0

        # Flags
        self.done = False
        self.error = None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def start_download(self):
        """
        Startet Mission Download vom Fahrzeug.
        """
        self.model.clear_mission()
        self.state = "REQUEST_COUNT"
        self.start_time = time.time()
        self.done = False
        self.error = None

    def start_upload(self, items):
        """
        Startet Mission Upload zum Fahrzeug.
        items = Liste von dicts mit seq, command, x, y, z
        """
        self.upload_items = items
        self.upload_index = 0
        self.state = "UPLOAD_COUNT"
        self.start_time = time.time()
        self.done = False
        self.error = None

    # ------------------------------------------------------------
    # FSM Tick
    # ------------------------------------------------------------
    def tick(self):
        """
        Wird vom MicroServiceController aufgerufen.
        """
        now = time.time()

        # Timeout
        if self.state not in {"IDLE", "DONE"}:
            if now - self.start_time > self.TIMEOUT:
                self.state = "ERROR"
                self.error = "Timeout"
                return

        # FSM
        if self.state == "IDLE":
            return

        # --------------------------------------------------------
        # DOWNLOAD
        # --------------------------------------------------------
        if self.state == "REQUEST_COUNT":
            self._send_mission_request_list()
            self.state = "WAIT_COUNT"
            return

        if self.state == "WAIT_COUNT":
            # Warten auf MISSION_COUNT
            return

        if self.state == "REQUEST_ITEMS":
            self._send_mission_request_item(self.received_items)
            self.state = "WAIT_ITEMS"
            return

        if self.state == "WAIT_ITEMS":
            # Warten auf MISSION_ITEM_INT
            return

        # --------------------------------------------------------
        # UPLOAD
        # --------------------------------------------------------
        if self.state == "UPLOAD_COUNT":
            self._send_mission_count(len(self.upload_items))
            self.state = "UPLOAD_ITEMS"
            return

        if self.state == "UPLOAD_ITEMS":
            if self.upload_index < len(self.upload_items):
                self._send_mission_item(self.upload_items[self.upload_index])
                self.upload_index += 1
                return
            else:
                self.state = "WAIT_UPLOAD_ACK"
                return

        if self.state == "WAIT_UPLOAD_ACK":
            # Warten auf MISSION_ACK
            return

        # --------------------------------------------------------
        # DONE / ERROR
        # --------------------------------------------------------
        if self.state == "DONE":
            self.done = True
            return

        if self.state == "ERROR":
            self.done = True
            return

    # ------------------------------------------------------------
    # Message Handling (Dispatcher ruft dies auf)
    # ------------------------------------------------------------
    def on_message(self, msg_type, msg):
        """
        Wird vom Dispatcher aufgerufen.
        """
        # --------------------------------------------------------
        # DOWNLOAD
        # --------------------------------------------------------
        if msg_type == "MISSION_COUNT" and self.state == "WAIT_COUNT":
            self.expected_count = msg.count
            self.received_items = 0
            self.state = "REQUEST_ITEMS"
            self.start_time = time.time()
            return

        if msg_type == "MISSION_ITEM_INT" and self.state == "WAIT_ITEMS":
            seq = msg.seq
            command = msg.command
            x = msg.x / 1e7
            y = msg.y / 1e7
            z = msg.z / 1000.0

            self.model.add_mission_item(seq, command, x, y, z)
            self.received_items += 1

            if self.received_items == self.expected_count:
                self.model.mission.ready = True
                self.state = "DONE"
            else:
                self.state = "REQUEST_ITEMS"

            self.start_time = time.time()
            return

        # --------------------------------------------------------
        # UPLOAD
        # --------------------------------------------------------
        if msg_type == "MISSION_ACK" and self.state == "WAIT_UPLOAD_ACK":
            self.state = "DONE"
            return

    # ------------------------------------------------------------
    # SEND COMMANDS
    # ------------------------------------------------------------
    def _send_mission_request_list(self):
        self.connection.master.mav.mission_request_list_send(
            self.connection.master.target_system,
            self.connection.master.target_component
        )

    def _send_mission_request_item(self, seq):
        self.connection.master.mav.mission_request_int_send(
            self.connection.master.target_system,
            self.connection.master.target_component,
            seq
        )

    def _send_mission_count(self, count):
        self.connection.master.mav.mission_count_send(
            self.connection.master.target_system,
            self.connection.master.target_component,
            count
        )

    def _send_mission_item(self, item):
        self.connection.master.mav.mission_item_int_send(
            self.connection.master.target_system,
            self.connection.master.target_component,
            item["seq"],
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            item["command"],
            0, 0, 0, 0, 0,
            int(item["x"] * 1e7),
            int(item["y"] * 1e7),
            int(item["z"] * 1000.0)
        )
