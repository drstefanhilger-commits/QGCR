# === PFAD-B FULL FILE: test_px4_sitl_harness.py ===

import subprocess
import time
import unittest
import os
import signal

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.model.model import Model


class TestPX4SITLHarness(unittest.TestCase):

    def setUp(self):
        sitl_root = os.path.expanduser("~/PX4-Autopilot")

        self.px4 = subprocess.Popen(
            ["make", "px4_sitl", "gz_rc_cessna"],
            cwd=sitl_root,
            preexec_fn=os.setsid,
        )

        self.model = Model()
        self.dispatcher = Dispatcher(self.model)
        self.connection = Connection(self.dispatcher)

    def tearDown(self):
        try:
            self.connection.close()
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

    def test_px4_heartbeat_pipeline(self):
        start = time.time()
        timeout = 60.0

        while time.time() - start < timeout:
            if self.model.px4_heartbeat_count >= 3:
                break
            time.sleep(0.2)

        self.assertGreaterEqual(
            self.model.px4_heartbeat_count,
            3,
            "PX4-SITL hat in der erwarteten Zeit keine Heartbeats bis ins Model geliefert",
        )

        self.assertTrue(self.model.px4_connected)
        self.assertIsNotNone(self.model.px4_mode)

        # ------------------------------------------------------------
        # Debug-Ausgabe: Unhandled Messages + STATUSTEXT
        # ------------------------------------------------------------
        print("\n--- Unhandled Message Stats ---")
        for msg_type, count in self.dispatcher.unhandled_stats.items():
            print(f"{msg_type}: {count}")

        print("\n--- Model Log Messages (last 10) ---")
        for severity, text in self.model.log_messages[-10:]:
            print(f"[{severity}] {text}")


if __name__ == "__main__":
    unittest.main()
