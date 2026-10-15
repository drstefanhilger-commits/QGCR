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
from QGCR.model.intercept import CHASE, HEAD_ON, latlon_to_enu
from QGCR.test.unittest.sitl_helper import (
    PX4Sitl, requires_sitl, gz_model_pose, assert_no_foreign_session, persisted_px4_param,
)


@requires_sitl
class TestPX4ApplicationIntercept(unittest.TestCase):
    """
    Echte Application mit gz_fsl_rocket_vtol, Bedienung über den FSL-Tab:
    Trigger (Nord 100 m, 20 m, 5 m/s nach Osten) → Lot-Fußpunkt (Wartepunkt) → nachfliegen
    bzw. entgegen per DO_REPOSITION → Treffen → Landung am Start. Prüft Plan, Gazebo-Marken,
    2D-Plot, minimalen Abstand und Flugweg; Akku-Abbruch über SIM_BAT_MIN_PCT.
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

    def east_north(self, p):
        """(lat, lon) → (Ost, Nord) [m] relativ zum Startpunkt der Planung."""
        return latlon_to_enu(self.model.intercept_origin, p[0], p[1])

    def fly_intercept(self, expected_mode, **fields):
        """Trigger über den FSL-Tab senden; Wartepunkt → entgegen/nachfliegen → Treffen → Landung."""
        m = self.model
        self.assertIn(persisted_px4_param("SIM_BAT_MIN_PCT"), (None, 50.0),
                      "SIM_BAT_MIN_PCT verstellt – Akku-RTL würde den Einsatz verfälschen")
        self.pump_until(lambda: m.hfsm_main == "READY" and m.ready_to_arm
                        and getattr(m, "mission_ms", None) is not None, 150, "READY")

        self.select_tab("FSL")
        self.pump_until(lambda: m.hfsm_main == "INTERCEPT", 5, "INTERCEPT")
        home = self.app.window.home_tab
        self.pump_until(lambda: str(home.takeoff_button["state"]) == "disabled", 3, "HomeTab gesperrt")
        self.assertEqual(str(home.model_combo["state"]), "disabled")

        tab = self.app.window.fsl_tab
        for key, value in fields.items():
            tab.vars[key].set(str(value))
        self.pump_until(lambda: str(tab.btn_trigger["state"]) == "normal", 5, "Trigger-Button")
        tab.btn_trigger.invoke()

        self.pump_until(lambda: m.hfsm_sub == "APPROACH", 30, "APPROACH")
        plan = m.intercept_plan
        self.assertTrue(plan.reachable, plan.reason)
        self.assertEqual(plan.mode, expected_mode)

        # 2D-Plot + Gazebo: Kreis, Trigger-Bahn, Wartepunkt, Treffpunkt
        self.pump_until(lambda: tab.plot.find_withtag("wait"), 5, "Wartepunkt im Plot")
        for tag in ("circle", "trigger_path", "start", "landing", "meet"):
            self.assertTrue(tab.plot.find_withtag(tag), tag)
        self.pump_until(lambda: gz_model_pose("qgcr_wait") is not None
                        and gz_model_pose("qgcr_trigger_path") is not None, 20, "Gazebo-Marken")
        wx, wy = gz_model_pose("qgcr_wait")
        self.assertLess(math.hypot(wx - plan.wait[0], wy - plan.wait[1]), 3.0)

        # Kürzester Weg zum Lot-Fußpunkt, Ankunft etwa zur geplanten Zeit
        trigger = m.intercept_trigger
        self.pump_until(lambda: m.hfsm_sub == "PURSUE", 120, "Wartepunkt erreicht (PURSUE)")
        arrival = time.time() - trigger.timestamp
        self.assertLess(abs(arrival - plan.t_fsl), 10.0,
                        f"Ankunft nach {arrival:.0f} s, geplant {plan.t_fsl:.0f} s")
        fe, fn = self.east_north((m.vehicle_lat, m.vehicle_lon))
        self.assertLess(math.hypot(fe - plan.wait[0], fn - plan.wait[1]), 3.0)
        self.assertEqual(m.intercept_pursuit.mode, expected_mode)
        self.assertIn(expected_mode, tab.lbl_plan["text"])

        # Treffen → zurück und landen
        self.pump_until(lambda: m.hfsm_sub != "PURSUE", 120, "Treffen")
        self.assertEqual(m.hfsm_sub, "RTL", m.intercept_status)
        self.assertIn("Treffpunkt erreicht", m.intercept_status)
        min_distance, _ = m.intercept_min_distance
        self.assertLessEqual(min_distance, 5.0)
        self.pump_until(lambda: tab.lbl_min_distance["text"].startswith("Min. Abstand: ")
                        and "-" not in tab.lbl_min_distance["text"], 3, "Min. Abstand im Tab")

        self.pump_until(lambda: m.hfsm_sub == "IDLE" and not m.px4_armed, 180, "gelandet")
        self.assertTrue(m.intercept_status.startswith("FSL gelandet – minimaler Abstand"), m.intercept_status)
        self.assertLess(math.hypot(*self.east_north(m.mission_track[-1])), 3.0, "nicht am Start gelandet")
        return plan

    def test_chase_to_landing(self):
        """Standard-Trigger: Trigger ist vor der FSL am Wartepunkt → nachfliegen (nach Osten)."""
        plan = self.fly_intercept(CHASE)
        self.assertTrue(any(self.east_north(p)[0] > plan.wait[0] + 20.0 for p in self.model.mission_track),
                        "FSL ist dem Trigger nicht nachgeflogen")

    def test_head_on_to_landing(self):
        """Trigger weit entfernt: FSL zuerst am Wartepunkt → entgegen (nach Westen)."""
        plan = self.fly_intercept(HEAD_ON, east=-400)
        self.assertTrue(any(self.east_north(p)[0] < plan.wait[0] - 20.0 for p in self.model.mission_track),
                        "FSL ist dem Trigger nicht entgegen geflogen")

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

        # Vorbedingung: normaler Default (ein früherer Abbruch kann 10 % hinterlassen haben)
        self.assertIn(persisted_px4_param("SIM_BAT_MIN_PCT"), (None, 50.0))

        # PX4 speichert Parameter in SITL dauerhaft → in jedem Fall zurücksetzen
        self.assertTrue(self.set_px4_param("SIM_BAT_MIN_PCT", 10.0), "SIM_BAT_MIN_PCT nicht gesetzt")
        try:
            self.select_tab("FSL")
            self.pump_until(lambda: m.hfsm_main == "INTERCEPT", 5, "INTERCEPT")
            tab = self.app.window.fsl_tab
            tab.vars["battery_min"].set("30")
            # weit entfernter, langsamer Trigger: Treffen erst nach dem Akku-Minimum
            for key, value in (("east", -900), ("v_east", 3), ("timeout", 600)):
                tab.vars[key].set(str(value))
            self.pump_until(lambda: str(tab.btn_trigger["state"]) == "normal", 5, "Trigger-Button")
            tab.btn_trigger.invoke()

            self.pump_until(lambda: m.hfsm_sub == "APPROACH", 30, "APPROACH")
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
            # PX4 speichert verzögert: erst beenden, wenn der Default auch gespeichert ist
            deadline = time.time() + 15.0
            while persisted_px4_param("SIM_BAT_MIN_PCT") not in (None, 50.0) and time.time() < deadline:
                self.app.root.update()
                time.sleep(0.2)
            self.assertIn(persisted_px4_param("SIM_BAT_MIN_PCT"), (None, 50.0),
                          "SIM_BAT_MIN_PCT ist noch gespeichert – PX4-Konsole: param set SIM_BAT_MIN_PCT 50")


if __name__ == "__main__":
    unittest.main()
