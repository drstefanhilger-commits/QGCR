#!/usr/bin/env python3
"""
harness_connection.py
---------------------

Stellt eine QGC-kompatible MAVLink-Verbindung bereit:
- Bindet an udp:0.0.0.0:14550 (wie QGC)
- Startet GCS-Heartbeat-Thread (1 Hz)
- Wartet auf PX4-Heartbeat (sysid=1)
- Liefert ein verbundenes MAVLink-Objekt zurück
"""

import time
import threading
from pymavlink import mavutil


class HarnessConnection:
    def __init__(self):
        self.master = None
        self.target_system = None
        self.target_component = None

    # ------------------------------------------------------------
    # Heartbeat-Thread
    # ------------------------------------------------------------
    def _gcs_heartbeat(self):
        while True:
            self.master.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0, 0, 0
            )
            time.sleep(1)

    # ------------------------------------------------------------
    # Auf PX4-Heartbeat warten
    # ------------------------------------------------------------
    def _wait_for_px4_heartbeat(self):
        while True:
            msg = self.master.recv_match(type="HEARTBEAT", blocking=True)
            sysid = msg.get_srcSystem()
            compid = msg.get_srcComponent()

            if sysid == 1:
                self.target_system = sysid
                self.target_component = compid
                return

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def connect(self):
        print("[CONN] Öffne MAVLink-Verbindung udp:0.0.0.0:14550")
        self.master = mavutil.mavlink_connection(
            "udp:0.0.0.0:14550",
            source_system=255,
            source_component=0
        )

        print("[CONN] Starte GCS-Heartbeat-Thread")
        threading.Thread(target=self._gcs_heartbeat, daemon=True).start()

        print("[CONN] Warte auf PX4-Heartbeat…")
        self._wait_for_px4_heartbeat()
        print(f"[CONN] PX4 erkannt: sysid={self.target_system}, compid={self.target_component}")

        return self.master, self.target_system, self.target_component
