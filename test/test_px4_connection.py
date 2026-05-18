# === PFAD-B FULL FILE: QGCR/test/test_px4_connection.py ===

import unittest
import subprocess
import time
import os
import signal
from pymavlink import mavutil

from QGCR.test.test_px4_connection_lib import TestConnection


class TestPX4Connection(unittest.TestCase):

    def setUp(self):
        sitl_root = os.path.expanduser("~/PX4-Autopilot")

        self.px4 = subprocess.Popen(
            ["make", "px4_sitl", "gz_rc_cessna"],
            cwd=sitl_root,
            preexec_fn=os.setsid,
        )

        self.mav_in = mavutil.mavlink_connection("udp:0.0.0.0:14550")
        self.conn = None

    def tearDown(self):
        if self.conn:
            self.conn.stop()

        try:
            os.killpg(os.getpgid(self.px4.pid), signal.SIGTERM)
        except Exception:
            pass

        try:
            self.px4.wait(timeout=10)
        except Exception:
            pass

    def test_connection_establishes_and_receives_heartbeats(self):
        print("[TEST-LOG] Warte auf PX4 HEARTBEAT ...")
        start = time.time()
        while time.time() - start < 20:
            msg = self.mav_in.recv_match(type="HEARTBEAT", blocking=False)
            if msg:
                print("[TEST-LOG] PX4 HEARTBEAT empfangen")
                break
            time.sleep(0.1)

        print("[TEST-LOG] Starte TestConnection ...")
        self.conn = TestConnection()
        self.conn.start()

        time.sleep(3.0)

        hb_count = 0
        start = time.time()
        while time.time() - start < 5.0:
            msg = self.mav_in.recv_match(type="HEARTBEAT", blocking=False)
            if msg:
                hb_count += 1
            time.sleep(0.1)

        print(f"[TEST-LOG] PX4 Heartbeats nach GCS-HB: {hb_count}")
        self.assertGreater(hb_count, 0)


if __name__ == "__main__":
    unittest.main()
