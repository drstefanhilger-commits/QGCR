# === PFAD-B FULL FILE: QGCR/microservices/upload_ms.py ===

import time
from pymavlink import mavutil


class UploadMicroService:
    """
    Mission Upload MicroService (FSM-Version)
    ----------------------------------------
    Zustände:

        IDLE
        SEND_COUNT
        SEND_ITEMS
        WAIT_ACK
        DONE
        ERROR

    Eigenschaften:
    - Non-blocking
    - Deterministisch
    - Tick() wird vom MicroServiceController aufgerufen
    - on_message() wird vom Dispatcher aufgerufen
    """

    TIMEOUT = 5.0

    def __init__(self, model, connection):
        self.model = model
        self.connection = connection

        # FSM
        self.state = "IDLE"
        self.start_time = 0.0

        # Upload-Daten
        self.items = None
        self.index = 0

        # Flags
        self.done = False
        self.error = None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def start(self, items):
        """
        Startet den Upload einer Mission.
        items = Liste von dicts mit seq, command, x, y, z
        """
        self.items = items
        self.index = 0

        self.state = "SEND_COUNT"
        self.start_time = time.time()

        self.done = False
        self.error = None

        print(f"[UploadMS] Upload gestartet, {len(items)} Items")

    # ------------------------------------------------------------
    # FSM Tick
    # ------------------------------------------------------------
    def tick(self):
        """
        Wird vom MicroServiceController aufgerufen.
        """
        if self.state == "IDLE":
            return

        now = time.time()

        # Timeout
        if self.state not in {"IDLE", "DONE"}:
            if now - self.start_time > self.TIMEOUT:
                self.state = "ERROR"
                self.error = "Timeout"
                print("[UploadMS] ERROR: Timeout")
                return

        # --------------------------------------------------------
        # SEND_COUNT
        # --------------------------------------------------------
        if self.state == "SEND_COUNT":
            self._send_mission_count(len(self.items))
            self.state = "SEND_ITEMS"
            self.start_time = now
            return

        # --------------------------------------------------------
        # SEND_ITEMS
        # --------------------------------------------------------
        if self.state == "SEND_ITEMS":
            if self.index < len(self.items):
                self._send_mission_item(self.items[self.index])
                print(f"[UploadMS] Sende Item {self.index}")
                self.index += 1
                self.start_time = now
                return
            else:
                self.state = "WAIT_ACK"
                self.start_time = now
                print("[UploadMS] Alle Items gesendet, warte auf ACK")
                return

        # --------------------------------------------------------
        # WAIT_ACK
        # --------------------------------------------------------
        if self.state == "WAIT_ACK":
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
    # Message Handling
    # ------------------------------------------------------------
    def on_message(self, msg_type, msg):
        """
        Dispatcher ruft dies auf.
        """
        if msg_type == "MISSION_ACK" and self.state == "WAIT_ACK":
            print("[UploadMS] MISSION_ACK empfangen → DONE")
            self.state = "DONE"
            return

    # ------------------------------------------------------------
    # SEND COMMANDS
    # ------------------------------------------------------------
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
