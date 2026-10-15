# === PFAD-B FULL FILE: QGCR/test/unittest/test_intercept_intercept_hfsm.py ===

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from pymavlink import mavutil

from QGCR.model.intercept import InterceptConfig, Trigger
from QGCR.sim.px4_swarm_starter import PX4InstanceConfig
from QGCR.states.intercept.intercept_hfsm import InterceptHFSM
from QGCR.states.main_state import MainState
from QGCR.test.unittest.dummy_model import DummyModel

M = mavutil.mavlink


class TestInterceptHFSM(unittest.TestCase):

    def setUp(self):
        m = self.model = DummyModel()
        m.px4_connected = True
        m.active_tab = "FSL"
        m.vehicle_lat, m.vehicle_lon = 47.397971, 8.546164
        m.vehicle_configs = [PX4InstanceConfig("/opt/px4", "gz_fsl_rocket_vtol", 1, verbose=False)]

        self.ms = MagicMock()
        self.ms.upload.return_value = True
        self.ms.last_error = None
        m.mission_ms = self.ms

        self.conn = MagicMock()
        self.conn.master.target_system = 1
        self.conn.master.target_component = 1
        m.connection = self.conn

        self.fsm = InterceptHFSM(m)
        self.fsm.on_update()                                   # enter

    def trigger(self, **kw):
        values = dict(drone_id="T1", timestamp=time.time(), east=-150, north=100, up=20, v_east=5, v_north=0)
        values.update(kw)
        self.model.intercept_trigger = Trigger(**values)
        self.model.hfsm_events.append("INTERCEPT_TRIGGER")
        return self.fsm.on_update()

    def tick_until(self, cond, timeout=2.0):
        deadline = time.time() + timeout
        state = self.fsm.on_update()
        while not cond() and time.time() < deadline:
            time.sleep(0.01)
            state = self.fsm.on_update()
        return state

    def sent(self):
        return [c.args[0].command for c in self.conn.send.call_args_list]

    def fly(self):
        self.trigger()
        self.tick_until(lambda: self.model.hfsm_sub == "START")
        self.model.px4_armed = True
        self.model.px4_mode = "AUTO.MISSION"
        self.fsm.on_update()
        self.assertEqual(self.model.hfsm_sub, "FLIGHT")

    # --------------------------------------------------------
    def test_enter(self):
        self.assertEqual(self.model.hfsm_main, "INTERCEPT")
        self.assertEqual(self.model.hfsm_sub, "IDLE")

    def test_trigger_plans_uploads_and_starts(self):
        self.trigger()
        self.assertEqual(self.model.hfsm_sub, "UPLOAD")
        self.assertTrue(self.model.intercept_plan.reachable)
        self.assertTrue(self.model.mission.ready)                         # Mission für Plot
        lat, lon = self.model.landing_point()
        self.assertAlmostEqual(lat, 47.397971, places=6)
        self.assertAlmostEqual(lon, 8.546164, places=6)

        self.tick_until(lambda: self.model.hfsm_sub == "START")
        items = self.ms.upload.call_args[0][0]
        self.assertEqual(items[0].command, M.MAV_CMD_NAV_TAKEOFF)
        self.assertEqual(self.sent(), [M.MAV_CMD_MISSION_START])

    def test_flight_until_landing(self):
        self.fly()
        self.assertTrue(self.model.mission_running)
        self.model.px4_armed = False                                    # gelandet
        self.assertEqual(self.fsm.on_update(), MainState.INTERCEPT)
        self.assertEqual(self.model.hfsm_sub, "IDLE")
        self.assertEqual(self.model.intercept_status, "FSL gelandet")
        self.assertFalse(self.model.mission_running)

    def test_unreachable_trigger(self):
        self.trigger(east=-30, v_east=30)
        self.assertEqual(self.model.hfsm_sub, "IDLE")
        self.ms.upload.assert_not_called()
        self.assertIn("kein Wartepunkt", self.model.intercept_status)

    def test_wrong_model_rejected(self):
        self.model.vehicle_configs[0].model_name = "gz_rc_cessna"
        self.trigger()
        self.assertEqual(self.model.hfsm_sub, "IDLE")
        self.assertIn("gz_fsl_rocket_vtol erforderlich", self.model.intercept_status)

    def test_only_one_trigger(self):
        self.fly()
        self.trigger(drone_id="T9")
        self.assertEqual(self.model.hfsm_sub, "FLIGHT")
        self.assertEqual(self.ms.upload.call_count, 1)

    def test_abort_in_flight_sends_rtl(self):
        self.fly()
        self.model.hfsm_events.append("INTERCEPT_ABORT")
        self.fsm.on_update()
        self.assertEqual(self.sent()[-1], M.MAV_CMD_NAV_RETURN_TO_LAUNCH)
        self.assertEqual(self.model.hfsm_sub, "RTL")

    def test_timeout_sends_rtl(self):
        self.model.intercept_config = InterceptConfig(timeout=5)
        self.fly()
        with patch("QGCR.states.intercept.intercept_hfsm.time.time", return_value=time.time() + 6):
            self.fsm.on_update()
        self.assertEqual(self.sent()[-1], M.MAV_CMD_NAV_RETURN_TO_LAUNCH)
        self.assertIn("Timeout", self.model.intercept_status)

    def test_low_battery_sends_rtl(self):
        self.fly()
        self.model.update_battery(25)
        self.fsm.on_update()
        self.assertEqual(self.sent()[-1], M.MAV_CMD_NAV_RETURN_TO_LAUNCH)
        self.assertIn("Akku 25 %", self.model.intercept_status)

    def test_rtl_sent_only_once(self):
        self.fly()
        self.model.update_battery(10)
        self.fsm.on_update()
        self.fsm.on_update()
        self.assertEqual(self.sent().count(M.MAV_CMD_NAV_RETURN_TO_LAUNCH), 1)

    def test_abort_during_upload_cancels(self):
        release = threading.Event()
        def upload(items, cancel=None):
            cancel.wait(2)
            self.ms.last_error = "Abgebrochen"
            return False
        self.ms.upload.side_effect = upload
        self.trigger()
        self.model.hfsm_events.append("INTERCEPT_ABORT")
        self.fsm.on_update()
        self.tick_until(lambda: self.model.hfsm_sub == "IDLE")
        self.assertIn("Upload fehlgeschlagen", self.model.intercept_status)
        self.conn.send.assert_not_called()

    def test_start_rejected_after_timeout(self):
        self.trigger()
        self.tick_until(lambda: self.model.hfsm_sub == "START")
        with patch("QGCR.states.intercept.intercept_hfsm.time.time", return_value=time.time() + 11):
            self.fsm.on_update()
        self.assertEqual(self.model.hfsm_sub, "IDLE")
        self.assertIn("abgelehnt", self.model.intercept_status)

    def test_leaving_tab_goes_ready_only_on_ground(self):
        self.fly()
        self.model.active_tab = "Home"
        self.assertEqual(self.fsm.on_update(), MainState.INTERCEPT)     # im Flug bleiben
        self.model.px4_armed = False
        self.fsm.on_update()                                            # gelandet → IDLE
        self.assertEqual(self.fsm.on_update(), MainState.READY)

    def test_reset_in_flight_lands_first(self):
        self.fly()
        self.model.hfsm_events.append("RESET")
        self.assertEqual(self.fsm.on_update(), MainState.INTERCEPT)
        self.assertEqual(self.sent()[-1], M.MAV_CMD_NAV_RETURN_TO_LAUNCH)
        self.model.px4_armed = False
        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_reset_on_ground_is_immediate(self):
        self.model.hfsm_events.append("RESET")
        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_connection_lost_goes_reset(self):
        self.model.px4_connected = False
        self.assertEqual(self.fsm.on_update(), MainState.RESET)


if __name__ == "__main__":
    unittest.main()
