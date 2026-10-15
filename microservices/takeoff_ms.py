# === PFAD-B FULL FILE: QGCR/microservices/takeoff_ms.py ===

import time
from pymavlink import mavutil


class TakeoffMicroService:
    STATE_IDLE = "IDLE"
    STATE_ARMING = "ARMING"
    STATE_MODE = "MODE"
    STATE_TAKEOFF = "TAKEOFF"
    STATE_DONE = "DONE"
    STATE_ERROR = "ERROR"

    TIMEOUT = 5.0

    @property
    def active(self):
        return self.state not in (
            self.STATE_IDLE,
            self.STATE_DONE,
            self.STATE_ERROR
        )

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
        # Bereits aktiv? → Start ignorieren
        if self.active:
            print("[TakeoffMS] Start ignoriert: bereits aktiv")
            return
            
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

        # Zielhöhe braucht die Home-Höhe (AMSL) – prüfen, BEVOR gearmt wird
        if self.takeoff_params() is None:
            print("[TakeoffMS] Start abgebrochen: Home-Höhe unbekannt")
            self.state = "ERROR"
            self.error = "home altitude unknown"
            self.done = True
            return

        self.state = "SEND_ARM"
        self.start_time = time.time()

        self.done = False
        self.error = None

        print(f"[TakeoffMS] Start → Zielhöhe {alt:.1f} m")

    def reset(self):
        """
        Zurück nach IDLE (nach Landung / RESET): bricht eine laufende
        Sequenz ab, der nächste TAKEOFF startet wieder von vorn.
        """
        self.state = self.STATE_IDLE
        self.done = False
        self.error = None

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
            try:
                self._send_takeoff()
            except Exception as e:
                print(f"[TakeoffMS] ERROR: {e}")
                self.state = "ERROR"
                self.error = str(e)
                self.done = True
                return
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
                    
                    # ⭐ HFSM-Event senden
                    try:
                        self.model.hfsm_events.append("TAKEOFF_DONE")
                    except Exception:
                        print("[TakeoffMS] WARN: TAKEOFF_DONE konnte nicht gesendet werden")

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

    def takeoff_params(self):
        """
        (lat, lon, alt_amsl) für MAV_CMD_NAV_TAKEOFF.
        PX4 erwartet param7 als Höhe über dem Meer (AMSL) und param5/6 als
        Zielposition (NaN = aktuelle Position; 0/0 wäre wörtlich 0°N 0°O).
        Zielhöhe = Home-Höhe (AMSL, HOME_POSITION) + self.alt (relativ).
        None, wenn die Home-Höhe noch unbekannt ist.
        """
        home_alt = getattr(self.model, "home_alt", None)
        if home_alt is None:
            return None

        nan = float("nan")
        lat = self.model.vehicle_lat if self.model.vehicle_lat is not None else nan
        lon = self.model.vehicle_lon if self.model.vehicle_lon is not None else nan
        return lat, lon, home_alt + self.alt

    def _send_takeoff(self):
        """
        Sendet TAKEOFF Command (Zielhöhe self.alt über Home).
        """
        params = self.takeoff_params()
        if params is None:
            raise RuntimeError("Home-Höhe unbekannt (noch keine HOME_POSITION)")
        lat, lon, alt_amsl = params

        MAV_COMP_ID_AUTOPILOT1 = 1
        self.connection.master.mav.command_long_send(
            self.connection.master.target_system,
            MAV_COMP_ID_AUTOPILOT1,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,              # confirmation
            0, 0, 0,        # params 1-3 unused
            float("nan"),   # yaw: PX4 entscheidet
            lat,
            lon,
            alt_amsl
        )
        print(f"[TakeoffMS] MAV_CMD_NAV_TAKEOFF gesendet (lat={lat}, lon={lon}, "
              f"alt={alt_amsl:.1f} m AMSL = {self.alt:.1f} m über Home)")

