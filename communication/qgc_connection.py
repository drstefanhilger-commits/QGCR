#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/communication/qgc_connection.py ===
"""
qgc_connection.py
-----------------

QGC-kompatible MAVLink-Verbindung, vollständig entkoppelt:

- Bindet an udp:0.0.0.0:14550 (wie QGroundControl)
- Sendet GCS-Heartbeat (1 Hz, sysid=255)
- Wartet synchron auf PX4-Heartbeat (sysid in {1, 100, 107})
- Startet RX-Thread und routet alle Messages ausschließlich über den Dispatcher
- KEIN Zugriff auf Model, GUI oder FSM
"""

import time
import threading
from pymavlink import mavutil


class QGCConnection:
    PX4_SYSIDS = {1, 100, 107}

    def __init__(self, dispatcher):
        """
        :param dispatcher: Objekt mit route_message(msg_type, msg)
        """
        self.dispatcher = dispatcher

        self.master = None
        self.target_system = None
        self.target_component = None

        self._stop = False
        self._rx_thread = None
        self._hb_thread = None

    # ------------------------------------------------------------
    # GCS-Heartbeat-Thread
    # ------------------------------------------------------------
    def _gcs_heartbeat_loop(self):
        MAV_TYPE_GCS = 6
        MAV_AUTOPILOT_INVALID = 8
        MAV_STATE_ACTIVE = 4
        MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1

        while not self._stop:
            try:
                if self.master:
                    self.master.mav.heartbeat_send(
                        MAV_TYPE_GCS,
                        MAV_AUTOPILOT_INVALID,
                        0,
                        MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                        MAV_STATE_ACTIVE,
                    )
            except Exception:
                pass

            time.sleep(1.0)

    # ------------------------------------------------------------
    # Auf PX4-Heartbeat warten (synchron)
    # ------------------------------------------------------------
    def _wait_for_px4_heartbeat(self):
        while not self._stop:
            try:
                msg = self.master.recv_match(
                    type="HEARTBEAT",
                    blocking=True,
                    timeout=1.0,
                )
            except Exception:
                msg = None

            if msg is None:
                continue

            sysid = msg.get_srcSystem()
            compid = msg.get_srcComponent()

            if sysid in self.PX4_SYSIDS:
                self.target_system = sysid
                self.target_component = compid
                return

    # ------------------------------------------------------------
    # RX-Thread: MAVLink → Dispatcher
    # ------------------------------------------------------------
    def _rx_loop(self):
        while not self._stop:
            try:
                msg = self.master.recv_match(blocking=False)
                if msg is None:
                    time.sleep(0.005)
                    continue

                msg_type = msg.get_type()
                self.dispatcher.route_message(msg_type, msg)

            except Exception:
                time.sleep(0.01)

    # ------------------------------------------------------------
    # Verbindungsaufbau
    # ------------------------------------------------------------
    def connect(self):
        print("[QGC-CONN] Öffne MAVLink-Verbindung udp:0.0.0.0:14550")
        self.master = mavutil.mavlink_connection(
            "udp:0.0.0.0:14550",
            source_system=255,
            source_component=0,
        )

        print("[QGC-CONN] Starte GCS-Heartbeat-Thread")
        self._hb_thread = threading.Thread(
            target=self._gcs_heartbeat_loop,
            daemon=True,
        )
        self._hb_thread.start()

        print("[QGC-CONN] Warte auf PX4-Heartbeat…")
        self._wait_for_px4_heartbeat()

        print(
            f"[QGC-CONN] PX4 erkannt: sysid={self.target_system}, "
            f"compid={self.target_component}"
        )

        print("[QGC-CONN] Starte RX-Thread")
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            daemon=True,
        )
        self._rx_thread.start()

        return self.master, self.target_system, self.target_component

    # ------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------
    def close(self):
        self._stop = True
        time.sleep(0.05)
