# === PFAD-B FULL FILE: QGCR/microservices/takeoff_ms.py ===

import time
from pymavlink import mavutil


class TakeoffMicroService:
    """
    MicroService für ARM + TAKEOFF.
    FSM-Zustände:

        IDLE
        SEND_ARM
        WAIT_ARM_ACK
        SEND_TAKEOFF
        WAIT_TAKEOFF_ACK
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

        # Zielhöhe
        self.alt = 10.0

        # Flags
        self.done = False
        self.error = None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def start(self, alt=10.0):
        """
        Startet ARM + TAKEOFF Sequenz.
        """

        # Nur starten, wenn PX4 verbunden ist und target_system gesetzt wurde
        if not getattr(self.model, "px4_connected", False):
            print("[TakeoffMS] Start abgebrochen: PX4 nicht verbunden")
            self.state = "ERROR"
            self.error = "PX4 not connected"
            self.done = True
            return

        if (
            self.connection.master is None
            or self.connection.master.target_system == 0
        ):
            print("[TakeoffMS] Start abgebrochen: target_system == 0 (noch kein Heartbeat?)")
            self.state = "ERROR"
            self.error = "target_system not set"
            self.done = True
            return

        self.alt = alt

        self.state = "SEND_ARM"
        self.start_time = time.time()

        self.done = False
        self.error = None

        print(f"[TakeoffMS] Start → Zielhöhe {alt:.1f} m")

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

        # Heartbeat verloren während aktiver Sequenz?
        if self.state not in {"IDLE", "DONE", "ERROR"}:
            if not getattr(self.model, "px4_connected", True):
                print("[TakeoffMS] ERROR: PX4-Verbindung verloren")
                self.state = "ERROR"
                self.error = "PX4 disconnected"
                self.done = True
                return

        # Timeout nur für aktive Zustände, nicht für ERROR/DONE
        if self.state in {
            "SEND_ARM",
            "WAIT_ARM_ACK",
            "SEND_TAKEOFF",
            "WAIT_TAKEOFF_ACK",
        }:
            if now - self.start_time > self.TIMEOUT:
                self.state = "ERROR"
                self.error = f"Timeout in state {self.state}"
                print(f"[TakeoffMS] ERROR: Timeout in {self.state}")
                self.done = True
                return

        # --------------------------------------------------------
        # SEND_ARM
        # --------------------------------------------------------
        if self.state == "SEND_ARM":
            self._send_arm()
            self.state = "WAIT_ARM_ACK"
            self.start_time = now
            return

        # --------------------------------------------------------
        # WAIT_ARM_ACK
        # --------------------------------------------------------
        if self.state == "WAIT_ARM_ACK":
            # Warten auf COMMAND_ACK (ARM)
            return

        # --------------------------------------------------------
        # SEND_TAKEOFF
        # --------------------------------------------------------
        if self.state == "SEND_TAKEOFF":
            self._send_takeoff()
            self.state = "WAIT_TAKEOFF_ACK"
            self.start_time = now
            return

        # --------------------------------------------------------
        # WAIT_TAKEOFF_ACK
        # --------------------------------------------------------
        if self.state == "WAIT_TAKEOFF_ACK":
            # Warten auf COMMAND_ACK (TAKEOFF)
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
        if msg_type != "COMMAND_ACK":
            return

        print("[TakeoffMS] DEBUG: COMMAND_ACK received:", msg)

        # ARM ACK
        if self.state == "WAIT_ARM_ACK":
            if msg.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                if msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                    print("[TakeoffMS] ARM ACK → OK, sende TAKEOFF")
                    self.state = "SEND_TAKEOFF"
                    self.start_time = time.time()
                else:
                    print(f"[TakeoffMS] ARM ACK → ERROR ({msg.result})")
                    self.state = "ERROR"
                    self.error = f"ARM failed: {msg.result}"
                    self.done = True
                return

        # TAKEOFF ACK
        if self.state == "WAIT_TAKEOFF_ACK":
            if msg.command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
                if msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                    print("[TakeoffMS] TAKEOFF ACK → DONE")
                    self.state = "DONE"
                    self.done = True
                else:
                    print(f"[TakeoffMS] TAKEOFF ACK → ERROR ({msg.result})")
                    self.state = "ERROR"
                    self.error = f"TAKEOFF failed: {msg.result}"
                    self.done = True
                return

    # ------------------------------------------------------------
    # SEND COMMANDS
    # ------------------------------------------------------------
    def _send_arm(self):
        """
        Sendet ARM Command.
        """
        MAV_COMP_ID_AUTOPILOT1 = 1

        self.connection.master.mav.command_long_send(
            self.connection.master.target_system,
            MAV_COMP_ID_AUTOPILOT1,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,      # confirmation
            1,      # arm
            0, 0, 0, 0, 0, 0
        )
        print("[TakeoffMS] MAV_CMD_COMPONENT_ARM_DISARM gesendet")

    def _send_takeoff(self):
        """
        Sendet TAKEOFF Command.
        Nutzt aktuelle Position aus dem Model (falls vorhanden).
        """
        lat = self.model.vehicle_lat if self.model.vehicle_lat is not None else 0.0
        lon = self.model.vehicle_lon if self.model.vehicle_lon is not None else 0.0
        alt = self.alt

        MAV_COMP_ID_AUTOPILOT1 = 1
        self.connection.master.mav.command_long_send(
            self.connection.master.target_system,
            MAV_COMP_ID_AUTOPILOT1,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,          # confirmation
            0, 0, 0,    # params 1-3 unused
            0,          # yaw
            lat,
            lon,
            alt
        )
        print(f"[TakeoffMS] MAV_CMD_NAV_TAKEOFF gesendet (lat={lat}, lon={lon}, alt={alt})")

        print("[TakeoffMS] DEBUG: target_system =", self.connection.master.target_system)
        print("[TakeoffMS] DEBUG: target_component = 1")
        print("[TakeoffMS] DEBUG: vehicle_lat/lon =", self.model.vehicle_lat, self.model.vehicle_lon)

