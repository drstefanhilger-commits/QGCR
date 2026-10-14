# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_application_land.py ===

import gc
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from QGCR.main import Application
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl


@requires_sitl
class TestPX4ApplicationLand(unittest.TestCase):
    """
    Echte Application, Bedienung über die HomeTab-Buttons:
    TAKEOFF → steigen → LAND → gelandet + disarmed → READY, danach zweiter Flug.
    """

    def start_app(self, model_name):
        self._env = patch.dict(os.environ, {"HEADLESS": "1"})
        self._env.start()
        self._print = patch("builtins.print")
        self._print.start()
        self.tmp = tempfile.TemporaryDirectory()

        self.app = Application(model_name=model_name)
        self.app.root.withdraw()
        self.model = self.app.model
        self.model.base_path = self.tmp.name
        self.home = self.app.window.home_tab

    def tearDown(self):
        self.app.shutdown()
        PX4Sitl._kill_leftovers()
        del self.app
        gc.collect()
        self.tmp.cleanup()
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
                  f"mode={self.model.px4_mode}, armed={self.model.px4_armed}, "
                  f"alt={self.model.vehicle_alt}, takeoff={self.model.takeoff.state}/{self.model.takeoff.error})")

    def fly_and_land(self):
        self.pump_until(lambda: self.model.hfsm_main == "READY" and self.model.ready_to_arm,
                        60, "READY + ready_to_arm")

        self.home.takeoff_button.invoke()
        self.pump_until(lambda: self.model.hfsm_main == "AIRBORNE"
                        and self.model.px4_armed and self.model.vehicle_alt > 5.0,
                        60, "AIRBORNE > 5 m")

        self.home.land_button.invoke()
        self.pump_until(lambda: self.model.hfsm_sub == "LAND"
                        and self.model.px4_mode == "AUTO.LAND", 10, "AUTO.LAND")

        self.pump_until(lambda: self.model.hfsm_main == "READY", 120, "gelandet → READY")
        self.assertFalse(self.model.px4_armed)
        self.assertLess(self.model.vehicle_alt, 1.0)

    def check_two_flights(self, model_name):
        self.start_app(model_name)
        self.pump_until(lambda: self.model.hfsm_main == "READY", 150, "erstes READY")

        self.fly_and_land()
        self.fly_and_land()          # Takeoff-Service wurde zurückgesetzt

    def test_rocket_vtol(self):
        self.check_two_flights("gz_fsl_rocket_vtol")

    def test_rc_cessna(self):
        self.check_two_flights("gz_rc_cessna")


if __name__ == "__main__":
    unittest.main()
