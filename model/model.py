# === PFAD-B FULL FILE: QGCR/model/model.py ===

import math
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

    # Untermodi von AUTO (custom_mode Bits 24-31)
    PX4_AUTO_SUB_MODES = {
        1: "READY",
        2: "TAKEOFF",
        3: "LOITER",
        4: "MISSION",
        5: "RTL",
        6: "LAND",
        8: "FOLLOW_TARGET",
        9: "PRECLAND",
        10: "VTOL_TAKEOFF",
    }

    @classmethod
    def decode_px4_mode(cls, custom_mode):
        """
        PX4 custom_mode: Hauptmodus in Bits 16-23, Untermodus in Bits 24-31.
        Beispiel: AUTO (4) / LAND (6) → "AUTO.LAND".
        """
        main_mode = (custom_mode >> 16) & 0xFF
        sub_mode = (custom_mode >> 24) & 0xFF

        name = cls.PX4_MAIN_MODES.get(main_mode, f"MODE_{main_mode}")
        if main_mode == 4 and sub_mode:
            name += "." + cls.PX4_AUTO_SUB_MODES.get(sub_mode, f"SUB_{sub_mode}")
        return name

    # Auswählbare PX4/Gazebo-Modelle (make px4_sitl <name>)
    ALLOWED_MODELS = [
        "gz_rc_cessna",
        "gz_fsl_rocket_vtol",
    ]
    DEFAULT_MODEL = "gz_rc_cessna"

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
        self.allowed_models = list(self.ALLOWED_MODELS)

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
        self.px4_vehicle_type = None      # MAV_TYPE aus dem PX4-Heartbeat
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

        # Geflogener Track während einer Mission: [(lat, lon), ...] in Grad (2D-Plot)
        self.mission_track = []
        # Position beim Missionsstart (Home kann PX4 später, z. B. nach der Landung, neu setzen)
        self.mission_start_point = None

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
        self.px4_mode = self.decode_px4_mode(msg.custom_mode)

        self.px4_armed = bool(base_mode & self.MAV_MODE_FLAG_SAFETY_ARMED)

        self._lost_counter = 0
        self.px4_connected = True
        self.px4_vehicle_type = getattr(msg, "type", None)

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

    def reset_heartbeat(self):
        """
        Heartbeat-Status verwerfen (RESET / Modellwechsel):
        STARTUP wartet danach auf den Heartbeat der NEUEN PX4-Instanz.
        """
        self.px4_connected = False
        self.px4_last_heartbeat = 0.0
        self.px4_heartbeat_count = 0
        self.px4_vehicle_type = None
        self._lost_counter = 0

    # ------------------------------------------------------------
    # Missions-Track (2D-Plot)
    # ------------------------------------------------------------
    TRACK_MIN_DIST_M = 1.0      # neuer Punkt erst ab dieser Entfernung
    TRACK_MAX_POINTS = 10000

    def begin_mission(self):
        """Mission läuft ab jetzt: neuen Track beginnen, Startpunkt festhalten."""
        self.mission_running = True
        self.mission_track = []
        if self.vehicle_lat is not None and self.vehicle_lon is not None:
            self.mission_start_point = (self.vehicle_lat, self.vehicle_lon)
        elif self.home_lat is not None and self.home_lon is not None:
            self.mission_start_point = (self.home_lat, self.home_lon)
        else:
            self.mission_start_point = None

    def _record_track_point(self, lat, lon):
        if not self.mission_running or lat is None or lon is None:
            return
        if self.mission_track:
            last_lat, last_lon = self.mission_track[-1]
            dy = (lat - last_lat) * 111_320.0
            dx = (lon - last_lon) * 111_320.0 * math.cos(math.radians(lat))
            if dx * dx + dy * dy < self.TRACK_MIN_DIST_M ** 2:
                return
        if len(self.mission_track) >= self.TRACK_MAX_POINTS:
            return
        self.mission_track.append((lat, lon))

    def mission_markers(self):
        """
        (start, landing) als (lat, lon) oder None – für 2D-Plot und Gazebo.
        Start: Position beim Missionsstart, vorher Home. Landung: aus der Mission.
        """
        start = self.mission_start_point
        if start is None and self.home_lat is not None and self.home_lon is not None:
            start = (self.home_lat, self.home_lon)
        landing = self.landing_point() if self.mission.ready else None
        return start, landing

    def landing_point(self):
        """(lat, lon) der Landung aus der Mission (NAV_LAND / NAV_VTOL_LAND) oder None."""
        for item in reversed(self.mission.items):
            if item["command"] in (21, 85):
                return (item["x"], item["y"])
        return None

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
        self._record_track_point(lat, lon)

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