# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_application_mission_start.py ===

import gc
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from QGCR.main import Application
from QGCR.test.unittest.plan_fixture import write_flight_plan
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl, gz_model_pose


@requires_sitl
class TestPX4ApplicationMissionStart(unittest.TestCase):
    """
    Echte Application: Mission (mit Landung) hochladen, dann
    - vom Boden: MissionTab „Start“ → AIRBORNE/MISSION → Landung → READY
    - im Flug:   TAKEOFF → HomeTab „MISSION“ → Landung → READY

    VTOL: die Mission landet selbst.
    rc_cessna: PX4 v1.17 bricht die Festflügler-Missionslandung ab ("Holding at .. m above
    landing waypoint", PX4-seitig) – dort wird nach dem Missionsstart per LAND-Button gelandet.
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
        self.plan = write_flight_plan(model_name, directory=self.tmp.name)

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
        log = self.app.window.log_tab
        tail = lambda w: "\n".join(w.get("1.0", "end").strip().splitlines()[-15:])
        self.fail(f"Timeout: {what} (hfsm={self.model.hfsm_main}/{self.model.hfsm_sub}, "
                  f"mode={self.model.px4_mode}, armed={self.model.px4_armed}, "
                  f"alt={self.model.vehicle_alt}, status={self.model.mission_status})\n"
                  f"--- QGCR ---\n{tail(log.qgcr_text)}\n--- PX4 ---\n{tail(log.px4_text)}")

    def select_tab(self, text):
        nb = self.app.window.notebook
        for tab_id in nb.tabs():
            if nb.tab(tab_id, "text") == text:
                nb.select(tab_id)
        self.app.root.update()

    def upload_mission(self):
        self.pump_until(lambda: self.model.hfsm_main == "READY" and self.model.ready_to_arm
                        and getattr(self.model, "mission_ms", None) is not None,
                        150, "READY")
        self.select_tab("Mission")
        self.pump_until(lambda: self.model.hfsm_main == "MISSION", 5, "MISSION")
        self.app.gui_controller.request_mission_upload(self.plan)
        self.pump_until(lambda: self.model.hfsm_sub == "IDLE"
                        and self.model.mission_status.startswith("Upload ")
                        and "läuft" not in self.model.mission_status, 30, "Upload")
        self.assertTrue(self.model.mission_status.startswith("Upload OK"), self.model.mission_status)

    def wait_mission_landed(self, timeout, land_button=False):
        self.pump_until(lambda: self.model.hfsm_main == "AIRBORNE"
                        and self.model.hfsm_sub == "MISSION"
                        and self.model.px4_mode == "AUTO.MISSION", 30, "AIRBORNE/MISSION")
        self.select_tab("Home")      # nach der Landung READY (nicht gleich wieder MISSION)
        self.pump_until(lambda: self.model.vehicle_alt > 5.0, 90, "Mission steigt")

        if land_button:
            self.app.window.home_tab.land_button.invoke()
            self.pump_until(lambda: self.model.px4_mode == "AUTO.LAND", 10, "AUTO.LAND")

        self.pump_until(lambda: self.model.hfsm_main == "READY", timeout, "gelandet → READY")
        self.assertFalse(self.model.px4_armed)
        self.assertFalse(self.model.mission_running)

    def start_from_ground(self, model_name, timeout, land_button=False):
        self.start_app(model_name)
        self.upload_mission()

        tab = self.app.window.mission_tab
        self.pump_until(lambda: str(tab.btn_start["state"]) == "normal", 5, "Start-Button aktiv")
        tab.btn_start.invoke()
        self.wait_mission_landed(timeout, land_button)

    def start_in_flight(self, model_name, timeout, land_button=False):
        self.start_app(model_name)
        self.upload_mission()

        self.select_tab("Home")
        self.pump_until(lambda: self.model.hfsm_main == "READY", 5, "READY")
        home = self.app.window.home_tab
        home.takeoff_button.invoke()
        self.pump_until(lambda: self.model.hfsm_main == "AIRBORNE" and self.model.vehicle_alt > 5.0,
                        60, "TAKEOFF > 5 m")

        home.mission_button.invoke()
        self.wait_mission_landed(timeout, land_button)

    def test_rocket_vtol_from_ground(self):
        self.start_from_ground("gz_fsl_rocket_vtol", 180)

        # Gazebo: Start- und Landepunkt als Modelle (Mission startet/landet am Welt-Ursprung)
        for name in ("qgcr_start", "qgcr_landing"):
            pose = gz_model_pose(name)
            self.assertIsNotNone(pose, name)
            self.assertLess(abs(pose[0]) + abs(pose[1]), 3.0, (name, pose))

        # 2D-Plot: Track der Mission, Start- und Landepunkt
        self.assertGreater(len(self.model.mission_track), 10)
        self.pump_until(lambda: self.app.window.home_tab.canvas.find_withtag("track"), 5, "Track im Plot")
        plot = self.app.window.home_tab.canvas
        for tag in ("track", "start", "landing", "waypoints"):
            self.assertTrue(plot.find_withtag(tag), tag)

    def test_rocket_vtol_in_flight(self):
        self.start_in_flight("gz_fsl_rocket_vtol", 180)

    def test_rc_cessna_from_ground(self):
        self.start_from_ground("gz_rc_cessna", 120, land_button=True)

    def test_rc_cessna_in_flight(self):
        self.start_in_flight("gz_rc_cessna", 120, land_button=True)


if __name__ == "__main__":
    unittest.main()
