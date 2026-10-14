# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_application_shutdown.py ===

import gc
import os
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from QGCR.main import Application
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl


def pids(*pgrep_args):
    out = subprocess.run(["pgrep", *pgrep_args], capture_output=True, text=True).stdout
    return [int(p) for p in out.split()]


@requires_sitl
class TestPX4ApplicationShutdown(unittest.TestCase):
    """
    Echte Application startet PX4; shutdown() (wie Klick auf X) beendet PX4 + Gazebo.
    PX4 darf das Terminal nicht als stdin erben (sonst hängt das Terminal nach dem Beenden).
    """

    def setUp(self):
        self._env = patch.dict(os.environ, {"HEADLESS": "1"})
        self._env.start()
        self._print = patch("builtins.print")
        self._print.start()
        self.tmp = tempfile.TemporaryDirectory()

        self.app = Application(model_name="gz_rc_cessna")
        self.app.root.withdraw()
        self.app.model.base_path = self.tmp.name

    def tearDown(self):
        self.app.shutdown()
        PX4Sitl._kill_leftovers()
        del self.app
        gc.collect()
        self.tmp.cleanup()
        self._print.stop()
        self._env.stop()

    def test_shutdown_stops_px4_and_gazebo(self):
        deadline = time.time() + 150
        while time.time() < deadline and self.app.model.hfsm_main != "READY":
            self.app.root.update()
            time.sleep(0.05)
        self.assertEqual(self.app.model.hfsm_main, "READY")

        px4 = pids("-x", "px4")
        self.assertEqual(len(px4), 1)
        self.assertTrue(os.readlink(f"/proc/{px4[0]}/fd/0").startswith("pipe:"))

        # PX4-Shell darf nicht endlos Prompts ausgeben (EOF auf stdin)
        px4_log = self.app.window.log_tab.px4_text.get("1.0", "end")
        self.assertLess(px4_log.count("pxh>"), 5)

        self.app.shutdown()

        deadline = time.time() + 10
        while time.time() < deadline and (pids("-x", "px4") or pids("-f", "^gz sim")):
            time.sleep(0.2)
        self.assertEqual(pids("-x", "px4"), [])
        self.assertEqual(pids("-f", "^gz sim"), [])


if __name__ == "__main__":
    unittest.main()
