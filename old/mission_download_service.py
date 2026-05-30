# === PFAD-B FULL FILE: QGCR/services/mission_download_service.py ===

from pymavlink import mavutil
import time


class MissionDownloadService:
    """
    Einfacher Missions-Download-Service für PX4 über den GCS-Port 14550.

    - Stellt eine MAVLink-Verbindung her
    - Sendet GCS-Heartbeats, damit PX4 uns als Ground Control Station erkennt
    - Sendet MISSION_REQUEST_LIST
    - Verarbeitet MISSION_COUNT und MISSION_ITEM_INT
    """

    def __init__(self, model, system_id: int = 255, component_id: int = 190):
        self.model = model
        self.system_id = system_id
        self.component_id = component_id

        # GCS-Port: wir hören auf 14550, PX4 sendet von 18570
        self.mav = mavutil.mavlink_connection(
            "udp:0.0.0.0:14550",
            source_system=self.system_id,
            source_component=self.component_id,
        )

        self.expected_items = 0
        self._last_heartbeat = 0.0
        self._heartbeat_interval = 1.0  # Sekunden

    # ------------------------------------------------------------------
    # GCS-Heartbeat
    # ------------------------------------------------------------------
    def send_heartbeat_if_needed(self):
        """
        Sendet in regelmäßigen Abständen einen GCS-HEARTBEAT.
        PX4 erkennt uns dann als Ground Control Station und aktiviert
        Mission-Manager, Parameter-Manager etc.
        """
        now = time.time()
        if now - self._last_heartbeat >= self._heartbeat_interval:
            self.mav.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0,  # base_mode
                0,  # custom_mode
                0,  # system_status
            )
            self._last_heartbeat = now

    # ------------------------------------------------------------------
    # Missions-Download
    # ------------------------------------------------------------------
    def start_download(self):
        """
        Startet den Missions-Download, indem MISSION_REQUEST_LIST gesendet wird.
        Vorher wird ein HEARTBEAT gesendet, damit PX4 uns sicher als GCS sieht.
        """
        # Sicherstellen, dass mindestens ein Heartbeat rausging
        self.send_heartbeat_if_needed()

        self.mav.mav.mission_request_list_send(
            target_system=1,
            target_component=1,
        )

    def on_mission_count(self, msg):
        """
        Verarbeitet MISSION_COUNT und bereitet die interne Liste vor.
        """
        self.expected_items = msg.count
        self.model.mission_waypoints.clear()

    def on_mission_item_int(self, msg):
        """
        Verarbeitet MISSION_ITEM_INT und fügt Items zur Modell-Mission hinzu.
        """
        self.model.mission_waypoints.append(msg)
        if len(self.model.mission_waypoints) == self.expected_items:
            self.model.mission_loaded = True

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def close(self):
        try:
            self.mav.close()
        except Exception:
            pass
