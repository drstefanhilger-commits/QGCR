# === PFAD-B FULL FILE: QGCR/test/unittest/test_startup_hfsm.py ===

import unittest
from unittest.mock import MagicMock, patch

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.main_state import MainState


class TestStartupHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.vehicle_configs = ["cfg"]

    @patch("QGCR.states.startup.startup_hfsm.PX4SwarmStarter")
    def test_enter_starts_px4(self, starter_cls):
        fsm = StartupHFSM(self.model)
        state = fsm.on_update()

        self.assertEqual(state, MainState.STARTUP)
        starter_cls.assert_called_once_with(["cfg"], model=self.model)
        starter_cls.return_value.start_all.assert_called_once()
        self.assertIs(self.model.startup_controller, starter_cls.return_value)
        self.assertEqual(self.model.hfsm_main, "STARTUP")

    @patch("QGCR.states.startup.startup_hfsm.PX4SwarmStarter")
    def test_enter_reuses_existing_controller(self, starter_cls):
        existing = MagicMock()
        self.model.startup_controller = existing

        fsm = StartupHFSM(self.model)
        fsm.on_update()

        starter_cls.assert_not_called()
        self.assertIs(fsm.startup_controller, existing)

    @patch("QGCR.states.startup.startup_hfsm.PX4SwarmStarter")
    def test_waits_for_heartbeat(self, starter_cls):
        fsm = StartupHFSM(self.model)

        self.assertEqual(fsm.on_update(), MainState.STARTUP)
        self.assertEqual(fsm.on_update(), MainState.STARTUP)

    @patch("QGCR.states.startup.startup_hfsm.PX4SwarmStarter")
    def test_heartbeat_goes_ready(self, starter_cls):
        fsm = StartupHFSM(self.model)
        fsm.on_update()

        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 1

        self.assertEqual(fsm.on_update(), MainState.READY)

    @patch("QGCR.states.startup.startup_hfsm.PX4SwarmStarter")
    def test_start_error_is_logged(self, starter_cls):
        starter_cls.return_value.start_all.side_effect = RuntimeError("boom")

        fsm = StartupHFSM(self.model)
        state = fsm.on_update()

        self.assertEqual(state, MainState.STARTUP)
        self.assertIn("[QGCR] [StartupHFSM] PX4 start error: boom", self.model.qgcr_logs())


if __name__ == "__main__":
    unittest.main()
