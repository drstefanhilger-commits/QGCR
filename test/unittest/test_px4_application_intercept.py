# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_application_intercept.py ===

import gc
import math
import threading
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from pymavlink import mavutil

from QGCR.main import Application
from QGCR.model.intercept import enu_to_latlon
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl, gz_model_pose, assert_no_foreign_session


@requires_sitl
class TestPX4ApplicationIntercept(unittest.TestCase):
    """
    Echte Application mit gz_fsl_rocket_vtol, Bedienung über den FSL-Tab:
    Trigger (Ost -150 m, Nord 100 m, 20 m, 5 m/s nach Osten) → Wartepunkt → Mission →
    Warten/Folgen → Landung am Start. Prüft Plan, Gazebo-Marken, 2D-Plot und Flugweg.
    """

    def setUp(self):
        self._env = patch.dict(os.environ, {"HEADLESS": "1"})
        self._env.start()
        self._print = patch("builtins.print")
        self._print.start()
        self.tmp = tempfile.TemporaryDirectory()

        assert_no_foreign_session()

        self.app = Application(model_name="gz_fsl_rocket_vtol")
        self.app.root.withdraw()
        self.model = self.app.model
        self.model.base_path = self.tmp.name

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
        tail = lambda w: "\n".join(w.get("1.0", "end").strip().splitlines()[-20:])
        self.fail(f"Timeout: {what} (hfsm={self.model.hfsm_main}/{self.model.hfsm_sub}, "
                  f"mode={self.model.px4_mode}, armed={self.model.px4_armed}, "
                  f"status={self.model.intercept_status})\n--- QGCR ---\n{tail(log.qgcr_text)}")

    def select_tab(self, text):
        nb = self.app.window.notebook
        for tab_id in nb.tabs():
            if nb.tab(tab_id, "text") == text:
                nb.select(tab_id)
        self.app.root.update()

    def test_trigger_to_landing(self):
        m = self.model
        self.pump_until(lambda: m.hfsm_main == "READY" and m.ready_to_arm
                        and getattr(m, "mission_ms", None) is not None, 150, "READY")

        self.select_tab("FSL")
        self.pump_until(lambda: m.hfsm_main == "INTERCEPT", 5, "INTERCEPT")
        home = self.app.window.home_tab
        self.pump_until(lambda: str(home.takeoff_button["state"]) == "disabled", 3, "HomeTab gesperrt")
        self.assertEqual(str(home.model_combo["state"]), "disabled")

        tab = self.app.window.fsl_tab
        self.pump_until(lambda: str(tab.btn_trigger["state"]) == "normal", 5, "Trigger-Button")
        tab.btn_trigger.invoke()

        self.pump_until(lambda: m.hfsm_sub == "FLIGHT", 30, "FLIGHT")
        plan = m.intercept_plan
        self.assertTrue(plan.reachable, plan.reason)
        wait_ll = enu_to_latlon(m.intercept_origin, plan.wait[0], plan.wait[1])

        # 2D-Plot + Gazebo: Kreis, Trigger-Bahn, Wartepunkt
        self.pump_until(lambda: tab.plot.find_withtag("wait"), 5, "Wartepunkt im Plot")
        for tag in ("circle", "trigger_path", "start", "landing"):
            self.assertTrue(tab.plot.find_withtag(tag), tag)
        self.pump_until(lambda: gz_model_pose("qgcr_wait") is not None
                        and gz_model_pose("qgcr_trigger_path") is not None, 20, "Gazebo-Marken")
        wx, wy = gz_model_pose("qgcr_wait")
        self.assertLess(math.hypot(wx - plan.wait[0], wy - plan.wait[1]), 3.0)

        # Flug: Ankunftszeit am Wartepunkt messen, dann Landung am Start
        def dist_to_wait():
            return math.hypot((m.vehicle_lat - wait_ll[0]) * 111_320.0,
                              (m.vehicle_lon - wait_ll[1]) * 111_320.0 * math.cos(math.radians(wait_ll[0])))
        arrival = []
        def landed():
            if not arrival and dist_to_wait() < 3.0:
                arrival.append(time.time())
            return m.hfsm_sub == "IDLE" and not m.px4_armed
        self.pump_until(landed, 240, "gelandet")

        # rechtzeitig: FSL am Wartepunkt, bevor der Trigger 10 m davor ist (+2 s Toleranz)
        trigger = m.intercept_trigger
        self.assertTrue(arrival, "Wartepunkt nie erreicht")
        deadline = trigger.timestamp + plan.t_trigger - 10.0 / trigger.ground_speed
        self.assertLess(arrival[0], deadline + 2.0,
                        f"zu spät: {arrival[0] - trigger.timestamp:.1f} s, Soll ≤ {deadline - trigger.timestamp:.1f} s")
        self.assertEqual(m.intercept_status, "FSL gelandet")

        def dist_m(p, q):
            return math.hypot((p[0] - q[0]) * 111_320.0,
                              (p[1] - q[1]) * 111_320.0 * math.cos(math.radians(p[0])))
        self.assertLess(min(dist_m(p, wait_ll) for p in m.mission_track), 5.0)
        self.assertLess(dist_m(m.mission_track[-1], m.intercept_origin), 3.0)

    # ------------------------------------------------------------
    # Akku-Abbruch (Variante 1): SIM_BAT_MIN_PCT senken → RTL
    # ------------------------------------------------------------
    def set_px4_param(self, name, value, timeout=10.0):
        """PARAM_SET senden und auf die Bestätigung (PARAM_VALUE) warten."""
        confirmed = threading.Event()
        dispatcher = self.app.dispatcher
        original = dispatcher.dispatch

        def hook(msg):
            if msg.get_type() == "PARAM_VALUE" and msg.param_id == name \
                    and abs(msg.param_value - value) < 1e-3:
                confirmed.set()
            original(msg)

        dispatcher.dispatch = hook
        try:
            master = self.app.connection.master
            msg = mavutil.mavlink.MAVLink_param_set_message(
                master.target_system, master.target_component, name.encode(), float(value),
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
            deadline = time.time() + timeout
            while not confirmed.is_set() and time.time() < deadline:
                self.app.connection.send(msg)
                end = time.time() + 1.0
                while time.time() < end and not confirmed.is_set():
                    self.app.root.update()
                    time.sleep(0.05)
            return confirmed.is_set()
        finally:
            dispatcher.dispatch = original

    def test_low_battery_triggers_rtl(self):
        m = self.model
        self.pump_until(lambda: m.hfsm_main == "READY" and m.ready_to_arm
                        and getattr(m, "mission_ms", None) is not None, 150, "READY")

        # PX4 speichert Parameter in SITL dauerhaft → in jedem Fall zurücksetzen
        self.assertTrue(self.set_px4_param("SIM_BAT_MIN_PCT", 10.0), "SIM_BAT_MIN_PCT nicht gesetzt")
        try:
            self.select_tab("FSL")
            self.pump_until(lambda: m.hfsm_main == "INTERCEPT", 5, "INTERCEPT")
            tab = self.app.window.fsl_tab
            tab.vars["battery_min"].set("30")
            self.pump_until(lambda: str(tab.btn_trigger["state"]) == "normal", 5, "Trigger-Button")
            tab.btn_trigger.invoke()

            self.pump_until(lambda: m.hfsm_sub == "FLIGHT", 30, "FLIGHT")
            self.pump_until(lambda: m.hfsm_sub == "RTL", 90, "RTL wegen Akku")
            self.assertRegex(m.intercept_status, r"^Akku \d+ % < 30 % → zurück zum Start")
            self.assertLess(m.battery_remaining, 30)

            self.pump_until(lambda: m.hfsm_sub == "IDLE" and not m.px4_armed, 180, "nach RTL gelandet")
            dist = math.hypot((m.vehicle_lat - m.intercept_origin[0]) * 111_320.0,
                              (m.vehicle_lon - m.intercept_origin[1]) * 111_320.0
                              * math.cos(math.radians(m.intercept_origin[0])))
            self.assertLess(dist, 3.0, "nicht am Start gelandet")
        finally:
            self.assertTrue(self.set_px4_param("SIM_BAT_MIN_PCT", 50.0), "SIM_BAT_MIN_PCT nicht zurückgesetzt")


if __name__ == "__main__":
    unittest.main()
