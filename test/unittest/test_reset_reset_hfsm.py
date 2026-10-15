# === PFAD-B FULL FILE: QGCR/test/unittest/test_reset_reset_hfsm.py ===

import tempfile
import unittest
from unittest.mock import MagicMock

from QGCR.states.reset.reset_hfsm import ResetHFSM
from QGCR.states.main_state import MainState
from QGCR.test.unittest.dummy_model import DummyModel


class TestResetHFSM(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.model = DummyModel()
        self.model.base_path = self.tmp.name          # Backup nicht ins cwd schreiben
        self.model.takeoff = MagicMock()
        self.starter = MagicMock()
        self.model.startup_controller = self.starter

        # Zustand einer laufenden PX4-Instanz
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 42
        self.model.px4_last_heartbeat = 1e12
        self.model.px4_vehicle_type = 1

        self.fsm = ResetHFSM(self.model)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reset_stops_px4_and_goes_startup(self):
        self.assertEqual(self.fsm.on_update(), MainState.STARTUP)

        self.starter.stop_all.assert_called_once()
        self.assertIsNone(self.model.startup_controller)
        self.assertTrue(self.model.reset_done)

    def test_reset_clears_heartbeat_state(self):
        self.fsm.on_update()

        self.assertFalse(self.model.px4_connected)
        self.assertEqual(self.model.px4_heartbeat_count, 0)
        self.assertIsNone(self.model.px4_vehicle_type)
        self.assertFalse(self.model.heartbeat_ok())

    def test_reset_drops_pending_messages_of_old_px4(self):
        self.model.connection = MagicMock()
        self.fsm.on_update()
        self.model.connection.clear_pending.assert_called_once()

    def test_reset_clears_mission_running(self):
        self.model.mission_running = True
        self.fsm.on_update()
        self.assertFalse(self.model.mission_running)

    def test_check_timeout_after_reset_stays_disconnected(self):
        self.fsm.on_update()

        for _ in range(3):
            self.model.check_timeout()
        self.assertFalse(self.model.connection_ready())


if __name__ == "__main__":
    unittest.main()
