# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_application_model_switch.py ===

import os
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from pymavlink import mavutil

from QGCR.main import Application
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl


def count_procs(*pgrep_args):
    out = subprocess.run(["pgrep", *pgrep_args], capture_output=True, text=True).stdout
    return len(out.split())


@requires_sitl
class TestPX4ApplicationModelSwitch(unittest.TestCase):
    """
    Echte Application: Start mit gz_rc_cessna, Wechsel über die HomeTab-Auswahlliste
    auf gz_fsl_rocket_vtol → RESET → STARTUP → READY mit VTOL-Heartbeat.
    """

    def setUp(self):
        self._env = patch.dict(os.environ, {"HEADLESS": "1"})
        self._env.start()
        self._print = patch("builtins.print")
        self._print.start()
        self.tmp = tempfile.TemporaryDirectory()

        self.app = Application(model_name="gz_rc_cessna")
        self.app.root.withdraw()
        self.model = self.app.model
        self.model.base_path = self.tmp.name       # Reset-Backup nicht ins cwd

    def tearDown(self):
        self.app.stop()
        starter = getattr(self.model, "startup_controller", None)
        if starter is not None:
            starter.stop_all()
        PX4Sitl._kill_leftovers()
        self.app.root.destroy()
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
                  f"type={self.model.px4_vehicle_type}, hb={self.model.px4_heartbeat_count}, "
                  f"connected={self.model.px4_connected})\n{self.log_tail()}")

    def log_tail(self, n=25):
        """Letzte Zeilen aus QGCR- und PX4-Log (Diagnose bei Timeout)."""
        log = self.app.window.log_tab
        qgcr = log.qgcr_text.get("1.0", "end").strip().splitlines()[-n:]
        px4 = log.px4_text.get("1.0", "end").strip().splitlines()[-n:]
        return "--- QGCR ---\n" + "\n".join(qgcr) + "\n--- PX4 ---\n" + "\n".join(px4)

    def ready_with(self, mav_type):
        return (self.model.hfsm_main == "READY"
                and self.model.px4_vehicle_type == mav_type)

    def test_switch_cessna_to_rocket_vtol(self):
        fixed_wing = mavutil.mavlink.MAV_TYPE_FIXED_WING
        vtol = mavutil.mavlink.MAV_TYPE_VTOL_QUADROTOR

        self.pump_until(lambda: self.ready_with(fixed_wing), 150, "READY mit rc_cessna")

        old_pid = self.model.px4_pid

        combo = self.app.window.home_tab.model_combo
        self.assertEqual(combo.get(), "gz_rc_cessna")
        combo.set("gz_fsl_rocket_vtol")
        combo.event_generate("<<ComboboxSelected>>")

        # RESET kann nur einen Tick dauern → nicht per Abtastung von hfsm_main prüfen,
        # sondern über neue PX4-Instanz (PID) und das QGCR-Log
        self.pump_until(lambda: self.ready_with(vtol)
                        and self.model.px4_pid not in (None, old_pid),
                        180, "READY mit fsl_rocket_vtol (neue PX4-Instanz)")

        qgcr_log = self.app.window.log_tab.qgcr_text.get("1.0", "end")
        self.assertIn("HFSM-Wechsel: READY → RESET", qgcr_log)
        self.assertIn("HFSM-Wechsel: RESET → STARTUP", qgcr_log)
        self.assertEqual(combo.get(), "gz_fsl_rocket_vtol")
        self.assertEqual(count_procs("-x", "px4"), 1)
        self.assertEqual(count_procs("-f", "^gz sim"), 1)


if __name__ == "__main__":
    unittest.main()
