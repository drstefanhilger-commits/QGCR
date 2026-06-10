# === PFAD-B FULL FILE: QGCR/test/test_px4_mission_download_harness.py ===

import subprocess
import time
import unittest
import os
import signal
from pymavlink import mavutil

from QGCR.communication.gcs_heartbeat_sender import GCSHeartbeatSender


class TestPX4MissionDownloadHarness(unittest.TestCase):

    def setUp(self):
        sitl_root = os.path.expanduser("~/PX4-Autopilot")

        # PX4 starten
        self.px4 = subprocess.Popen(
            ["make", "px4_sitl", "gz_rc_cessna"],
            cwd=sitl_root,
            preexec_fn=os.setsid,
        )

        # PX4 → GCS (Instanz #0)
        self.mav_in = mavutil.mavlink_connection("udp:0.0.0.0:14550")

        # Noch KEIN GCS-Heartbeat starten!
        self.gcs_hb = None

    def tearDown(self):
        try:
            if self.gcs_hb:
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

    def test_mission_download(self):
        # 1) PX4-Heartbeat abwarten
        print("[TEST-LOG] Warte auf PX4 HEARTBEAT ...")
        start = time.time()
        while time.time() - start < 20:
            msg = self.mav_in.recv_match(type="HEARTBEAT", blocking=False)
            if msg:
                print("[TEST-LOG] PX4 HEARTBEAT empfangen")
                break
            time.sleep(0.1)

        # 2) Jetzt erst GCS-Heartbeat starten
        print("[TEST-LOG] Starte GCSHeartbeatSender ...")
        self.gcs_hb = GCSHeartbeatSender()
        self.gcs_hb.start()

        # 3) PX4 Zeit geben, den GCS zu erkennen
        time.sleep(2.0)

        # 4) Mission Request List senden
        print("[TEST-LOG] Sende MISSION_REQUEST_LIST ...")
        self.mav_in.mav.mission_request_list_send(
            target_system=1,
            target_component=1
        )

        mission_count = None
        items = {}

        start = time.time()
        while time.time() - start < 10:
            msg = self.mav_in.recv_match(blocking=False)
            if not msg:
                time.sleep(0.05)
                continue

            if msg.get_type() == "MISSION_COUNT":
                mission_count = msg.count
                print(f"[TEST-LOG] MISSION_COUNT empfangen: {mission_count}")

                # Jetzt alle Items anfordern
                for seq in range(mission_count):
                    self.mav_in.mav.mission_request_int_send(
                        target_system=1,
                        target_component=1,
                        seq=seq
                    )

            elif msg.get_type() == "MISSION_ITEM_INT":
                items[msg.seq] = msg
                print(f"[TEST-LOG] MISSION_ITEM_INT empfangen: seq={msg.seq}")

            elif msg.get_type() == "MISSION_ACK":
                print(f"[TEST-LOG] MISSION_ACK empfangen: {msg.type}")

            if mission_count is not None and len(items) == mission_count:
                break

        # 5) Validierung
        self.assertIsNotNone(mission_count, "MISSION_COUNT wurde nicht empfangen")
        self.assertEqual(len(items), mission_count, "Nicht alle Mission Items empfangen")

        print("[TEST-LOG] Mission Download erfolgreich")


if __name__ == "__main__":
    unittest.main()
