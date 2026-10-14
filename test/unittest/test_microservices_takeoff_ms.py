# === PFAD-B FULL FILE: QGCR/test/unittest/test_microservices_takeoff_ms.py ===

import unittest
from unittest.mock import MagicMock, patch

from QGCR.microservices.takeoff_ms import TakeoffMicroService
from QGCR.test.unittest.dummy_model import DummyModel


@patch("builtins.print")
class TestMicroservicesTakeoffMs(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
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


if __name__ == "__main__":
    unittest.main()
