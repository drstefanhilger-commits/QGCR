# === PFAD-B FULL FILE: QGCR/test/unittest/test_ready_mission_fsm.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.ready.subfsms.ready_mission_fsm import ReadyMissionFSM
from QGCR.states.ready.ready_substate import ReadySubState


class TestReadyMissionFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 1
        self.model.mission_loaded = True
        self.fsm = ReadyMissionFSM(self.model)

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, ReadySubState.READY_MISSION)

    def test_enter_pushes_status(self):
        self.fsm.on_update()
        self.assertIn(("status", "Ready: Mission Tab"), self.model.gui_items())

    def test_stays_in_mission(self):
        self.assertEqual(self.fsm.on_update(), ReadySubState.READY_MISSION)

    def test_takeoff_not_allowed(self):
        self.model.gui_events.append("TAKEOFF")
        self.assertEqual(self.fsm.on_update(), ReadySubState.READY_MISSION)

    def test_tab_home_returns_to_idle(self):
        self.model.gui_events.append("GUI_TAB_HOME")
        self.assertEqual(self.fsm.on_update(), ReadySubState.READY_IDLE)

    def test_mission_removed_returns_to_idle(self):
        self.model.mission_loaded = False
        self.assertEqual(self.fsm.on_update(), ReadySubState.READY_IDLE)

    def test_heartbeat_lost(self):
        self.model.px4_connected = False
        self.assertEqual(self.fsm.on_update(), ReadySubState.READY_HEARTBEAT_LOST)


if __name__ == "__main__":
    unittest.main()
