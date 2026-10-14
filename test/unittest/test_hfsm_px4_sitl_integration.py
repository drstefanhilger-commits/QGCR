# === PFAD-B FULL FILE: test_hfsm_px4_sitl_integration.py ===

import subprocess
import time
import unittest
import os
import signal

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.model.model import Model
from QGCR.states.main.main_hfsm import MainHFSM


def kill_existing_px4():
    os.system("pkill -9 px4 2>/dev/null")


class TestHFSMWithPX4SITL(unittest.TestCase):

    def setUp(self):
        kill_existing_px4()

        sitl_root = os.path.expanduser(os.environ.get("PX4_DIR", "~/PX4-Autopilot"))

        self.px4 = subprocess.Popen(
            ["make", "px4_sitl", "gz_rc_cessna"],
            cwd=sitl_root,
            preexec_fn=os.setsid,
            stdin=subprocess.DEVNULL,
        )

        self.model = Model()
        self.dispatcher = Dispatcher(self.model)
        self.connection = Connection(self.dispatcher)

        self.hfsm = MainHFSM(self.model)

    def tearDown(self):
        try:
            self.connection.close()
        except:
            pass

        try:
            os.killpg(os.getpgid(self.px4.pid), signal.SIGTERM)
        except:
            pass

        try:
            self.px4.wait(timeout=10)
        except:
            pass

        kill_existing_px4()

    def test_hfsm_ready_with_px4_sitl(self):
        start = time.time()
        timeout = 30.0

        # Warten, bis Heartbeats ankommen
        while time.time() - start < timeout:
            if self.model.px4_heartbeat_count >= 3:
                break
            time.sleep(0.2)

        self.assertGreaterEqual(
            self.model.px4_heartbeat_count,
            3,
            "PX4-SITL hat in der erwarteten Zeit keine Heartbeats bis ins Model geliefert",
        )

        # MainHFSM sollte im READY-State sein und dort bleiben
        self.assertEqual(self.hfsm.state_enum.name, "READY")

        print("\nHFSM aktueller Zustand:", self.hfsm.state_enum.name)
        print("Heartbeat Count:", self.model.px4_heartbeat_count)
        print("Home Position:", self.model.home_lat, self.model.home_lon)


if __name__ == "__main__":
    unittest.main()
