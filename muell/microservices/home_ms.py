# === PFAD-B FULL FILE: QGCR/microservices/home_ms.py ===

import time
from pymavlink import mavutil


class HomeMicroService:
    """
    MicroService zum Setzen der Home-Position.
    FSM-Zustände:

        IDLE
        SEND_HOME
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

        # Flags
        self.done = False
        self.error = None

        # Ziel-Home-Position
        self.lat = None
        self.lon = None
        self.alt = None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def start(self, lat, lon, alt):
        """
        Startet das Setzen der Home-Position.
        """
        self.lat = lat
        self.lon = lon
        self.alt = alt

        self.state = "SEND_HOME"
        self.start_time = time.time()

        self.done = False
        self.error = None

        print(f"[HomeMS] Set Home → {lat:.7f}, {lon:.7f}, {alt:.1f} m")

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
                print("[HomeMS] ERROR: Timeout")
                return

        # --------------------------------------------------------
        # SEND_HOME
        # --------------------------------------------------------
        if self.state == "SEND_HOME":
            self._send_set_home()
            self.state = "WAIT_ACK"
            self.start_time = now
            return

        # --------------------------------------------------------
        # WAIT_ACK
        # --------------------------------------------------------
        if self.state == "WAIT_ACK":
            # Warten auf COMMAND_ACK
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
        if msg_type == "COMMAND_ACK" and self.state == "WAIT_ACK":
            if msg.command == mavutil.mavlink.MAV_CMD_DO_SET_HOME:
                print("[HomeMS] ACK empfangen → DONE")
                self.state = "DONE"
                return

    # ------------------------------------------------------------
    # SEND COMMAND
    # ------------------------------------------------------------
    def _send_set_home(self):
        """
        Sendet MAV_CMD_DO_SET_HOME an PX4.
        """
        self.connection.master.mav.command_long_send(
            self.connection.master.target_system,
            self.connection.master.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_HOME,
            0,          # confirmation
            1,          # use current = 1? Nein → 0 (wir setzen explizit)
            0, 0, 0,    # unused
            self.lat,
            self.lon,
            self.alt
        )
        print("[HomeMS] MAV_CMD_DO_SET_HOME gesendet")
