# === PFAD-B FULL FILE: QGCR/test/test_px4_connection_lib.py ===

import threading
import time
from pymavlink import mavutil


class TestConnection:
    """
    Minimalistische, stabile MAVLink-Test-Connection für PX4-SITL.
    """

    def __init__(self, sysid_px4=1, compid_px4=1, sysid_gcs=255, compid_gcs=190):
        self.sysid_px4 = sysid_px4
        self.compid_px4 = compid_px4
        self.sysid_gcs = sysid_gcs
        self.compid_gcs = compid_gcs

        self.master = None
        self.running = False

        self.recv_thread = None
        self.hb_thread = None
        self.monitor_thread = None

        self._lock = threading.Lock()
        self._last_rx = 0.0
        self._last_tx = 0.0
        self._rx_timeout = 5.0

    def start(self):
        if self.running:
            return

        self.running = True
        self._connect()

        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()

        self.hb_thread = threading.Thread(target=self._hb_loop, daemon=True)
        self.hb_thread.start()

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self.running = False

        if self.recv_thread:
            self.recv_thread.join(timeout=0.5)
        if self.hb_thread:
            self.hb_thread.join(timeout=0.5)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=0.5)

        with self._lock:
            if self.master:
                try:
                    self.master.close()
                except Exception:
                    pass
                self.master = None

    def _connect(self):
        with self._lock:
            if self.master:
                try:
                    self.master.close()
                except Exception:
                    pass

            self.master = mavutil.mavlink_connection(
                "udpout:127.0.0.1:14550",
                source_system=self.sysid_gcs,
                source_component=self.compid_gcs,
            )

            self.master.target_system = self.sysid_px4
            self.master.target_component = self.compid_px4

            self._last_rx = time.time()
            self._last_tx = time.time()

    def _recv_loop(self):
        while self.running:
            with self._lock:
                master = self.master

            if master is None:
                time.sleep(0.1)
                continue

            try:
                msg = master.recv_match(blocking=True, timeout=0.2)
            except Exception:
                time.sleep(0.2)
                continue

            if msg:
                self._last_rx = time.time()

    def _hb_loop(self):
        while self.running:
            with self._lock:
                master = self.master

            if master:
                try:
                    master.mav.heartbeat_send(
                        mavutil.mavlink.MAV_TYPE_GCS,
                        mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                        0,
                        0,
                        mavutil.mavlink.MAV_STATE_ACTIVE,
                    )
                    self._last_tx = time.time()
                except Exception:
                    pass

            time.sleep(1.0)

    def _monitor_loop(self):
        while self.running:
            if time.time() - self._last_rx > self._rx_timeout:
                self._connect()
                time.sleep(1.0)
                continue

            time.sleep(0.5)
