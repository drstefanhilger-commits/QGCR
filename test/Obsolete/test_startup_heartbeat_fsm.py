# === PFAD-B FULL FILE: QGCR/test/unittest/test_startup_heartbeat_fsm.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.startup.subfsms.startup_heartbeat_fsm import StartupHeartbeatFSM
from QGCR.states.startup.startup_substate import StartupSubState


class TestStartupHeartbeatFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = StartupHeartbeatFSM(self.model)

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, StartupSubState.STARTUP_HEARTBEAT)

    def test_enter_pushes_status(self):
        self.fsm.on_update()
        self.assertIn(("status", "Startup: Waiting for PX4 heartbeat"), self.model.gui_items())

    def test_no_heartbeat(self):
        next_state = self.fsm.on_update()
        self.assertEqual(next_state, StartupSubState.STARTUP_HEARTBEAT)

    def test_heartbeat_goes_to_params(self):
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 1

        next_state = self.fsm.on_update()
        self.assertEqual(next_state, StartupSubState.STARTUP_PARAMS)

    def test_connected_without_count_stays(self):
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 0

        next_state = self.fsm.on_update()
        self.assertEqual(next_state, StartupSubState.STARTUP_HEARTBEAT)


if __name__ == "__main__":
    unittest.main()
