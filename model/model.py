# === PFAD-B FULL FILE: QGCR/model/model.py ===

import time
from collections import deque


# ------------------------------------------------------------
# Mission-Datenstruktur
# ------------------------------------------------------------
class MissionData:
    def __init__(self):
        self.items = []      # Liste von Waypoints
        self.count = 0       # Anzahl
        self.ready = False   # Mission vollständig empfangen


# ------------------------------------------------------------
# Null-MicroService (Platzhalter)
# ------------------------------------------------------------
class _NullService:
    def __init__(self):
        self.done = False
        self.error = None

    def start(self):
        self.done = False
        self.error = None

    def tick(self):
        pass


# ------------------------------------------------------------
# Container für MicroServices
# ------------------------------------------------------------
class ServicesContainer:
    def __init__(self):
        self.param_sync = _NullService()
        self.mission    = _NullService()
        self.upload     = _NullService()
        self.home       = _NullService()
        self.takeoff    = _NullService()
        self.reset      = _NullService()


# ------------------------------------------------------------
# Zentrales Datenmodell
# ------------------------------------------------------------
class Model:
    HEARTBEAT_TIMEOUT = 8.0
    HEARTBEAT_DEBOUNCE_COUNT = 2
    MAV_MODE_FLAG_SAFETY_ARMED = 128

    PX4_MAIN_MODES = {
        1: "MANUAL",
        2: "ALTCTL",
        3: "POSCTL",
        4: "AUTO",
        5: "ACRO",
        6: "OFFBOARD",
        7: "STABILIZED",
        8: "RATTITUDE",
    }

    def __init__(self, queue_registry):
        self.queue_registry = queue_registry
        self.connection = None

        # MissionData (NICHT überschreiben!)
        self.mission = MissionData()

        # HFSM-Event-Queue
        self.hfsm_events = deque()

        # ------------------------------------------------------------
        # Modell-Informationen (NEU)
        # ------------------------------------------------------------

        # Liste erlaubter PX4/Gazebo-Modelle
        # Diese Liste wird vom Swarm-Starter validiert.
        self.allowed_models = [
            "gz_rc_cessna",
            "gz_x500",
            "gz_standard_vtol",
        ]

        # Modellname des aktiven Fahrzeugs (Single-PX4)
        # Wird vom px4_swarm_starter gesetzt.
        self.model_name: str | None = None

        # Modellnamen für Schwarmmitglieder
        # Beispiel: {1: "gz_rc_cessna", 2: "gz_x500"}
        self.swarm_model_names: dict[int, str] = {}

        # ------------------------------------------------------------
        # Heartbeat
        # ------------------------------------------------------------
        self.px4_connected = False
        self.px4_last_heartbeat = 0.0
        self.px4_heartbeat_count = 0
        self._lost_counter = 0

        # Telemetrie
        self.vehicle_lat = None
        self.vehicle_lon = None
        self.vehicle_alt = 0.0

        # Home Position
        self.home_lat = None
        self.home_lon = None
        self.home_alt = None

        # Mode/Armed
        self.px4_mode = "-"
        self.px4_armed = False
        self.ready_to_arm = False

        # Mission-Status
        self.mission_running = False
        self.mission_loaded = False

        # Mission-Upload/-Download (MISSION-HFSM)
        self.mission_upload_items = None   # MAVLink-Items aus .plan (GUIController)
        self.mission_upload_file = None
        self.mission_status = "-"

        # HFSM
        self.active_tab = "home"
        self.hfsm_main = "-"
        self.hfsm_sub = "-"

        # MicroServices
        self.services = ServicesContainer()

        # Aliase für HFSM (Variante B)
        self.takeoff    = self.services.takeoff
        self.home_ms    = self.services.home
        self.mission_ms = self.services.mission
        self.upload_ms  = self.services.upload
        self.reset      = self.services.reset 
        
        self._home_status_logged = False

        # Log-Nachrichten (max. 500 Einträge)
        self.log_messages = []
        self.max_log_entries = 500

        self.params_loaded = False

    # ------------------------------------------------------------
    # HFSM-Ready-Flags (für Startup/Ready/Airborne)
    # ------------------------------------------------------------
    def connection_ready(self):
        """PX4 hat mindestens einen Heartbeat gesendet."""
        return self.px4_connected

    def heartbeat_ok(self):
        """Mindestens ein Heartbeat empfangen."""
        return self.px4_heartbeat_count > 0

    def params_ready(self):
        """Parameter wurden geladen."""
        return self.params_loaded

    def mission_ready(self):
        """Mission vollständig empfangen."""
        return self.mission_loaded

    # ------------------------------------------------------------
    # HEARTBEAT
    # ------------------------------------------------------------
    def on_heartbeat(self, msg):
        now = time.time()
        self.px4_last_heartbeat = now
        self.px4_heartbeat_count += 1

        self.sysid = msg.get_srcSystem()
        self.compid = msg.get_srcComponent()

        base_mode = msg.base_mode
        custom_mode = msg.custom_mode
        main_mode = (custom_mode >> 24) & 0xFF
        self.px4_mode = self.PX4_MAIN_MODES.get(main_mode, f"MODE_{main_mode}")

        self.px4_armed = bool(base_mode & self.MAV_MODE_FLAG_SAFETY_ARMED)

        self._lost_counter = 0
        self.px4_connected = True

        try:
            self.queue_registry.require("gui").push(("telemetry", {
                "mode": self.px4_mode,
                "armed": self.px4_armed,
                "alt": self.vehicle_alt,
                "px4_hb": self.px4_heartbeat_count,
                "px4_connected": True
            }))
        except Exception:
            pass

    # ------------------------------------------------------------
    # TIMEOUT
    # ------------------------------------------------------------
    def check_timeout(self):
        now = time.time()
        dt = now - self.px4_last_heartbeat

        if dt > self.HEARTBEAT_TIMEOUT:
            self._lost_counter += 1
            if self._lost_counter >= self.HEARTBEAT_DEBOUNCE_COUNT:
                self.px4_connected = False
        else:
            self._lost_counter = 0
            self.px4_connected = True

        try:
            self.queue_registry.require("gui").push(("telemetry", {
                "mode": self.px4_mode,
                "armed": self.px4_armed,
                "alt": self.vehicle_alt,
                "px4_hb": self.px4_heartbeat_count,
                "px4_connected": self.px4_connected
            }))
        except Exception:
            pass

    # ------------------------------------------------------------
    # POSITION
    # ------------------------------------------------------------
    def update_vehicle_position(self, lat, lon, alt):
        self.vehicle_lat = lat
        self.vehicle_lon = lon
        self.vehicle_alt = alt

        try:
            self.queue_registry.require("gui").push(("telemetry", {
                "mode": self.px4_mode,
                "armed": self.px4_armed,
                "alt": alt,
                "px4_hb": self.px4_heartbeat_count,
                "px4_connected": self.px4_connected
            }))
        except Exception:
            pass

    def update_home_position(self, lat, lon, alt):
        self.home_lat = lat
        self.home_lon = lon
        self.home_alt = alt

        # Status nur einmal ausgeben
        if not getattr(self, "_home_status_logged", False):
            self._home_status_logged = True
            try:
                self.queue_registry.require("gui").push((
                    "status",
                    f"Home set: {lat:.5f}, {lon:.5f}, {alt:.1f} m"
                ))
            except Exception:
                pass

    # ------------------------------------------------------------
    # COMMAND ACK
    # ------------------------------------------------------------
    def on_command_ack(self, msg):
        try:
            self.queue_registry.require("gui").push((
                "status",
                f"ACK: {msg.command} → {msg.result}"
            ))
        except Exception:
            pass

    # ------------------------------------------------------------
    # Mission Management
    # ------------------------------------------------------------
    def clear_mission(self):
        self.mission.items = []
        self.mission.count = 0
        self.mission.ready = False

    def add_mission_item(self, seq, command, x, y, z):
        self.mission.items.append({
            "seq": seq,
            "command": command,
            "x": x,
            "y": y,
            "z": z
        })
        self.mission.count = len(self.mission.items)

    # ------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------
    def add_log(self, msg: str):
        self.log_messages.append(msg)
        if len(self.log_messages) > self.max_log_entries:
            self.log_messages.pop(0)

    def close_logfile(self):
        """
        Wird vom Stop-Button ausgelöst.
        Schließt das Logfile (aktuell: nur Log-Eintrag).
        """
        self.add_log("Logfile closed.")

    # ------------------------------------------------------------
    # State Update → GUI
    # ------------------------------------------------------------
    def push_state_update(self):
        try:
            self.queue_registry.require("gui").push((
                "state_update",
                {
                    "hfsm_main": self.hfsm_main,
                    "hfsm_sub": self.hfsm_sub,
                    "active_tab": self.active_tab
                }
            ))
        except Exception:
            self.add_log("State update pushed (no GUI)")

    def update_ready_to_arm(self, msg):
            """
            Wird von Connection bei HEARTBEAT aufgerufen.
            """
            try:
                # MAV_STATE_STANDBY = 3
                if getattr(msg, "system_status", None) == 3:
                    self.ready_to_arm = True
                else:
                    self.ready_to_arm = False
            except Exception:
                self.ready_to_arm = False