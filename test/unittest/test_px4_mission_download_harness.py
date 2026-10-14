# === PFAD-B FULL FILE: QGCR/test/test_px4_mission_download_harness.py ===

import unittest
import subprocess
import time
import os
import signal
from pymavlink import mavutil


class TestPX4MissionDownload(unittest.TestCase):

    def setUp(self):
        sitl_root = os.path.expanduser(os.environ.get("PX4_DIR", "~/PX4-Autopilot"))

        # PX4 starten
        self.px4 = subprocess.Popen(
            ["make", "px4_sitl", "gz_rc_cessna"],
            cwd=sitl_root,
            preexec_fn=os.setsid,
        )

        # EIN Socket: TX+RX über Port 14540 (Mission-Manager)
        self.mav = mavutil.mavlink_connection(
            "udp:0.0.0.0:14540",
            source_system=255,
            source_component=190,
        )

    def tearDown(self):
        try:
            os.killpg(os.getpgid(self.px4.pid), signal.SIGKILL)
        except Exception:
            pass

        try:
            self.px4.wait(timeout=5)
        except Exception:
            pass

        os.system("pkill -9 gzserver")
        os.system("pkill -9 gzclient")
        os.system("pkill -9 make")
        os.system("pkill -9 ninja")
        os.system("pkill -9 micrortps_agent")

    def _send_gcs_heartbeats(self, count=5, interval=0.5):
        for _ in range(count):
            self.mav.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0,
                0,
                mavutil.mavlink.MAV_STATE_ACTIVE,
            )
            time.sleep(interval)

    def test_mission_download(self):
        # 1) PX4-Heartbeat abwarten
        print("[TEST-LOG] Warte auf PX4 HEARTBEAT ...")
        start = time.time()
        hb = None
        while time.time() - start < 20:
            msg = self.mav.recv_match(type="HEARTBEAT", blocking=False)
            if msg:
                hb = msg
                target_system = msg.get_srcSystem()
                target_component = msg.get_srcComponent()
                print("[TEST-LOG] PX4 HEARTBEAT empfangen")
                break
            time.sleep(0.1)

        self.assertIsNotNone(hb, "Kein PX4 HEARTBEAT empfangen")

        # 2) GCS-Heartbeats senden
        print("[TEST-LOG] Sende GCS-Heartbeats ...")
        self._send_gcs_heartbeats()

        # 3) MISSION_REQUEST_LIST senden
        print("[TEST-LOG] Sende MISSION_REQUEST_LIST ...")
        self.mav.mav.mission_request_list_send(
            target_system,
            target_component,
        )

        mission_count = None
        items = {}

        # 4) MISSION_COUNT empfangen
        print("[TEST-LOG] Warte auf MISSION_COUNT ...")
        start = time.time()
        while time.time() - start < 5.0:
            msg = self.mav.recv_match(blocking=False)
            if msg and msg.get_type() == "MISSION_COUNT":
                mission_count = msg.count
                print(f"[TEST-LOG] MISSION_COUNT empfangen: {mission_count}")
                break
            time.sleep(0.1)

        self.assertIsNotNone(mission_count, "MISSION_COUNT wurde nicht empfangen")

        # 5) Mission Items anfordern
        for seq in range(mission_count):
            print(f"[TEST-LOG] Sende MISSION_REQUEST_INT für WP {seq} ...")
            self.mav.mav.mission_request_int_send(
                target_system,
                target_component,
                seq,
            )

            start = time.time()
            while time.time() - start < 5.0:
                msg = self.mav.recv_match(blocking=False)
                if msg and msg.get_type() == "MISSION_ITEM_INT" and msg.seq == seq:
                    items[seq] = msg
                    print(f"[TEST-LOG] MISSION_ITEM_INT empfangen: seq={seq}")
                    break
                time.sleep(0.1)

            self.assertIn(seq, items, f"MISSION_ITEM_INT seq={seq} wurde nicht empfangen")

        # 6) MISSION_ACK senden
        print("[TEST-LOG] Sende MISSION_ACK ...")
        self.mav.mav.mission_ack_send(
            target_system,
            target_component,
            mavutil.mavlink.MAV_MISSION_ACCEPTED
        )

        print("[TEST-LOG] Mission Download erfolgreich abgeschlossen.")
        self.assertEqual(len(items), mission_count)


if __name__ == "__main__":
    unittest.main()
