# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_application_mission.py ===

import gc
import os
import time
import unittest
from unittest.mock import patch

from QGCR.main import Application
from QGCR.test.unittest.plan_fixture import write_plan
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl


@requires_sitl
class TestPX4ApplicationMission(unittest.TestCase):
    """
    End-to-End mit der echten Application (startet PX4 selbst):
    READY → Mission-Tab → Upload (.plan) → Download → Home-Tab → READY.
    """

    def setUp(self):
        self._env = patch.dict(os.environ, {"HEADLESS": "1"})
        self._env.start()
        self._print = patch("builtins.print")
        self._print.start()

        self.app = Application()
        self.app.root.withdraw()
        self.model = self.app.model
        self.plan = write_plan()

    def tearDown(self):
        self.app.shutdown()
        PX4Sitl._kill_leftovers()
        del self.app
        gc.collect()
        os.remove(self.plan)
        self._print.stop()
        self._env.stop()

    def pump_until(self, cond, timeout, what):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.app.root.update()
            if cond():
                return
            time.sleep(0.05)
        self.fail(f"Timeout: {what} (hfsm={self.model.hfsm_main}/{self.model.hfsm_sub}, "
                  f"status={self.model.mission_status})")

    def select_tab(self, text):
        nb = self.app.window.notebook
        for tab_id in nb.tabs():
            if nb.tab(tab_id, "text") == text:
                nb.select(tab_id)
        self.app.root.update()

    def transfer_done(self, prefix):
        return self.model.hfsm_sub == "IDLE" and self.model.mission_status.startswith(prefix)

    def test_upload_download_roundtrip(self):
        self.pump_until(lambda: self.model.hfsm_main == "READY"
                        and getattr(self.model, "mission_ms", None) is not None,
                        150, "READY + MissionMicroService")

        self.select_tab("Mission")
        self.pump_until(lambda: self.model.hfsm_main == "MISSION", 5, "MISSION")

        # Upload (.plan statt Datei-Dialog)
        self.app.gui_controller.request_mission_upload(self.plan)
        self.pump_until(lambda: self.transfer_done("Upload "), 30, "Upload")
        self.assertEqual(self.model.mission_status, "Upload OK (3 Items)")

        # Mission im Model leeren, dann per Button herunterladen
        self.model.clear_mission()
        tab = self.app.window.mission_tab
        self.pump_until(lambda: str(tab.btn_download["state"]) == "normal", 5, "Download-Button aktiv")
        tab.btn_download.invoke()

        self.pump_until(lambda: self.transfer_done("Download "), 30, "Download")
        self.assertEqual(self.model.mission_status, "Download OK (3 Items)")
        self.assertEqual(self.model.mission.count, 3)
        self.assertAlmostEqual(self.model.mission.items[1]["x"], 47.3985, places=5)

        self.pump_until(lambda: tab.listbox.size() == 3, 5, "Wegpunkte im MissionTab")

        self.select_tab("Home")
        self.pump_until(lambda: self.model.hfsm_main == "READY", 5, "READY")


if __name__ == "__main__":
    unittest.main()
