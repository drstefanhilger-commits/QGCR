# === PFAD-B FULL FILE: QGCR/test/utils/px4_startup_synchronizer.py ===

import time
from pymavlink import mavutil

class PX4StartupSynchronizer:
    """
    Synchronisiert Tests mit PX4 über den GCS-Port 14550.
    Keine Ausgabe, nur stilles Warten auf MAVLink-Daten.
    """

    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout
        self._mav = mavutil.mavlink_connection("udp:0.0.0.0:14550")

    def wait_until_ready(self):
        start = time.time()
        first_msg = None

        while time.time() - start < self._timeout:
            msg = self._mav.recv_msg()
            if not msg:
                time.sleep(0.02)
                continue

            if first_msg is None:
                first_msg = msg

            if msg.get_type() == "HEARTBEAT":
                return msg

        if first_msg is not None:
            return first_msg

        raise TimeoutError("Keine MAVLink-Daten empfangen.")
