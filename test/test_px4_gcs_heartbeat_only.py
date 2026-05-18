# === PFAD-B FULL FILE: QGCR/test/test_px4_gcs_heartbeat_only.py ===

import subprocess
import time
import unittest
import os
import signal
from pymavlink import mavutil

from QGCR.communication.gcs_heartbeat_sender import GCSHeartbeatSender


class TestPX4GCSHeartbeatOnly(unittest.TestCase):

    def setUp(self):
        sitl_root = os.path.expanduser("~/PX4-Autopilot")

        self.px4 = subprocess.Popen(
            ["make", "px4_sitl", "gz_rc_cessna"],
            cwd=sitl_root,
            preexec_fn=os.setsid,
        )

        # PX4 → GCS (Instanz #0)
        self.mav_in = mavutil.mavlink_connection("udp:0.0.0.0:14550")

        # Noch KEIN Heartbeat-Thread starten!

    def tearDown(self):
        try:
            self.gcs_hb.stop()
        except Exception:
            pass

        try:
            os.killpg(os.getpgid(self.px4.pid), signal.SIGTERM)
        except Exception:
            pass

        try:
            self.px4.wait(timeout=10)
        except Exception:
            pass

    def test_gcs_heartbeat(self):
        # 1) PX4-Heartbeat abwarten
        while True:
            msg = self.mav_in.recv_match(type="HEARTBEAT", blocking=False)
            if msg:
                print("[TEST-LOG] PX4 HEARTBEAT empfangen")
                break
            time.sleep(0.1)

        # 2) Jetzt erst GCS-Heartbeat starten
        print("[TEST-LOG] Starte GCSHeartbeatSender ...")
        self.gcs_hb = GCSHeartbeatSender()
        self.gcs_hb.start()

        # 3) Zeit geben, damit PX4 mehrere GCS-HBs empfängt
        time.sleep(3.0)

        # 4) PX4-Heartbeats zählen
        hb_count = 0
        start = time.time()
        while time.time() - start < 5.0:
            msg = self.mav_in.recv_match(type="HEARTBEAT", blocking=False)
            if msg:
                hb_count += 1
            time.sleep(0.1)

        print(f"[TEST-LOG] PX4 Heartbeats nach GCS-HB: {hb_count}")
        self.assertGreater(hb_count, 0, "PX4 hat nicht auf GCS-Heartbeat reagiert")


if __name__ == "__main__":
    unittest.main()
