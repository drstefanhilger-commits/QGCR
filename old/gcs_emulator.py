# === PFAD-B FULL FILE: QGCR/services/gcs_emulator.py ===

import time
from typing import Dict, Tuple

from pymavlink import mavutil


class MiniQGC:
    """
    Minimaler QGC-Ersatz für PX4:
    - Öffnet eine MAVLink-Verbindung auf dem GCS-Port 14550
    - Sendet regelmäßig GCS-Heartbeats
    - Fordert explizit MISSION_COUNT an (MAV_CMD_REQUEST_MESSAGE)
    - Sendet MISSION_REQUEST_LIST
    - Verarbeitet MISSION_COUNT und MISSION_ITEM_INT
    """

    def __init__(
        self,
        system_id: int = 255,
        component_id: int = 190,
        local_port: int = 14550,
    ) -> None:
        self.system_id = system_id
        self.component_id = component_id

        self.mav = mavutil.mavlink_connection(
            f"udp:0.0.0.0:{local_port}",
            source_system=self.system_id,
            source_component=self.component_id,
        )

        self._last_heartbeat = 0.0
        self._heartbeat_interval = 1.0  # Sekunden

        self.expected_items: int = 0
        self.msg_stats: Dict[str, int] = {}
        self.got_count: bool = False
        self.got_items: int = 0

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------
    def send_heartbeat_if_needed(self) -> None:
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
    def start_mission_download(self) -> None:
        """
        Startet den Missions-Download:
        - sendet mindestens einen Heartbeat
        - fordert explizit MISSION_COUNT an (MAV_CMD_REQUEST_MESSAGE)
        - sendet MISSION_REQUEST_LIST
        """
        # Sicherstellen, dass PX4 uns als GCS sieht
        self.send_heartbeat_if_needed()
        time.sleep(0.1)

        # Explizit MISSION_COUNT anfordern (wie QGC über MAV_CMD_REQUEST_MESSAGE)
        self.mav.mav.command_long_send(
            1,  # target_system
            1,  # target_component
            mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
            0,  # confirmation
            mavutil.mavlink.MAVLINK_MSG_ID_MISSION_COUNT,  # param1: Message-ID
            0, 0, 0, 0, 0, 0,
        )

        time.sleep(0.1)

        # Missionsliste anfordern
        self.mav.mav.mission_request_list_send(
            target_system=1,
            target_component=1,
        )

    def step(self, model) -> None:
        """
        Ein Schritt im Event-Loop:
        - Heartbeat senden
        - eine MAVLink-Message lesen
        - Statistik aktualisieren
        - MISSION_COUNT / MISSION_ITEM_INT verarbeiten
        """
        self.send_heartbeat_if_needed()

        msg = self.mav.recv_msg()
        if not msg:
            return

        mtype = msg.get_type()
        self.msg_stats[mtype] = self.msg_stats.get(mtype, 0) + 1

        if mtype == "MISSION_COUNT":
            self.got_count = True
            self.expected_items = msg.count
            model.mission_waypoints.clear()

        elif mtype == "MISSION_ITEM_INT":
            self.got_items += 1
            model.mission_waypoints.append(msg)
            if len(model.mission_waypoints) == self.expected_items:
                model.mission_loaded = True

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    def run_until_complete(
        self,
        model,
        timeout: float = 45.0,
    ) -> Tuple[bool, int, Dict[str, int]]:
        """
        Führt den Missions-Download bis zum Abschluss oder Timeout aus.
        Gibt zurück:
        - got_count (bool)
        - got_items (int)
        - msg_stats (dict)
        """
        start = time.time()

        while time.time() - start < timeout and not model.mission_loaded:
            self.step(model)
            time.sleep(0.02)

        return self.got_count, self.got_items, dict(self.msg_stats)

    def close(self) -> None:
        try:
            self.mav.close()
        except Exception:
            pass
