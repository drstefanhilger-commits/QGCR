# === PFAD-B FULL FILE: QGCR/test/test_px4_home_position.py ===

import unittest
import subprocess
import time
import os
import signal
from pymavlink import mavutil


class TestPX4HomePosition(unittest.TestCase):

    def setUp(self):
        sitl_root = os.path.expanduser("~/PX4-Autopilot")

        # PX4 starten
        self.px4 = subprocess.Popen(
            ["make", "px4_sitl", "gz_rc_cessna"],
            cwd=sitl_root,
            preexec_fn=os.setsid,
        )

        # EIN Socket: TX+RX wie QGC
        self.mav = mavutil.mavlink_connection(
            "udpout:127.0.0.1:18570",
            source_system=255,
            source_component=190,
            input=True
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

    def test_home_position_request(self):
        # 1) PX4-Heartbeat abwarten
        print("[TEST-LOG] Warte auf PX4 HEARTBEAT ...")
        start = time.time()
        while time.time() - start < 20:
            msg = self.mav.recv_match(type="HEARTBEAT", blocking=False)
            if msg:
                print("[TEST-LOG] PX4 HEARTBEAT empfangen")
                break
            time.sleep(0.1)

        # 2) GCS-Heartbeats senden
        print("[TEST-LOG] Sende GCS-Heartbeats ...")
        for _ in range(5):
            self.mav.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0,
                0,
                mavutil.mavlink.MAV_STATE_ACTIVE,
            )
            time.sleep(0.5)

        # 3) HOME_POSITION anfordern
        print("[TEST-LOG] Sende REQUEST_MESSAGE für HOME_POSITION ...")
        self.mav.mav.command_long_send(
            1, 1,
            mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_HOME_POSITION,
            0, 0, 0, 0, 0, 0
        )

        # 4) HOME_POSITION empfangen
        home = None
        start = time.time()
        while time.time() - start < 5.0:
            msg = self.mav.recv_match(blocking=False)
            if msg and msg.get_type() == "HOME_POSITION":
                home = msg
                print("[TEST-LOG] HOME_POSITION empfangen")
                print(f"  lat: {home.latitude}")
                print(f"  lon: {home.longitude}")
                print(f"  alt: {home.altitude}")
                break
            time.sleep(0.1)

        self.assertIsNotNone(home, "HOME_POSITION wurde nicht empfangen")


if __name__ == "__main__":
    unittest.main()
