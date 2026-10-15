# === PFAD-B FULL FILE: QGCR/test/unittest/test_microservices_takeoff_ms.py ===

import math
import unittest
from unittest.mock import MagicMock, patch

from pymavlink import mavutil

from QGCR.microservices.takeoff_ms import TakeoffMicroService
from QGCR.test.unittest.dummy_model import DummyModel


@patch("builtins.print")
class TestMicroservicesTakeoffMs(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.model.update_home_position(47.0, 8.0, 488.0)     # Home 488 m AMSL
        self.conn = MagicMock()
        self.conn.master.target_system = 1
        self.ms = TakeoffMicroService(self.model, self.conn)

    def test_reset_returns_to_idle(self, _print):
        self.ms.start()
        self.assertTrue(self.ms.active)

        self.ms.reset()

        self.assertEqual(self.ms.state, TakeoffMicroService.STATE_IDLE)
        self.assertFalse(self.ms.done)
        self.assertIsNone(self.ms.error)
        self.assertFalse(self.ms.active)

    def test_reset_stops_sequence(self, _print):
        self.ms.start()
        self.ms.reset()
        self.ms.tick()

        self.conn.master.mav.command_long_send.assert_not_called()

    def test_restart_after_done_and_reset(self, _print):
        self.ms.state, self.ms.done = "DONE", True
        self.ms.reset()
        self.ms.start()

        self.assertEqual(self.ms.state, "SEND_ARM")

    # --------------------------------------------------------
    # TAKEOFF-Höhe: param7 ist AMSL
    # --------------------------------------------------------
    def sent_takeoff(self):
        for c in self.conn.master.mav.command_long_send.call_args_list:
            if c.args[2] == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
                return c.args
        return None

    def run_to_takeoff(self, alt=10.0):
        self.ms.start(alt=alt)
        self.ms.tick()                                    # ARM
        self.ms.state = "SEND_TAKEOFF"                    # ARM-ACK simuliert
        self.ms.tick()

    def test_takeoff_altitude_is_home_amsl_plus_target(self, _print):
        self.model.vehicle_lat, self.model.vehicle_lon = 47.001, 8.002
        self.run_to_takeoff(alt=10.0)

        args = self.sent_takeoff()
        self.assertEqual((args[8], args[9]), (47.001, 8.002))   # param5/6: aktuelle Position
        self.assertAlmostEqual(args[10], 498.0)                 # param7: 488 m AMSL + 10 m
        self.assertTrue(math.isnan(args[7]))                    # yaw: PX4 entscheidet
        self.assertEqual(self.ms.state, "WAIT_TAKEOFF_ACK")

    def test_unknown_position_sends_nan_not_zero(self, _print):
        self.run_to_takeoff()

        args = self.sent_takeoff()
        self.assertTrue(math.isnan(args[8]) and math.isnan(args[9]))

    def test_unknown_home_altitude_refuses_before_arming(self, _print):
        self.model.home_alt = None
        self.ms.start()

        self.assertEqual(self.ms.state, "ERROR")
        self.assertEqual(self.ms.error, "home altitude unknown")
        self.ms.tick()
        self.conn.master.mav.command_long_send.assert_not_called()   # kein ARM

    def test_send_error_sets_error_state(self, _print):
        self.run_to_takeoff()
        self.ms.state = "SEND_TAKEOFF"
        self.model.home_alt = None                        # z. B. Home verloren
        self.ms.tick()

        self.assertEqual(self.ms.state, "ERROR")
        self.assertIn("Home-Höhe unbekannt", self.ms.error)


if __name__ == "__main__":
    unittest.main()
