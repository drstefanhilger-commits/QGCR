# === PFAD-B FULL FILE: QGCR/test/unittest/test_ready_idle_fsm.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.ready.subfsms.ready_idle_fsm import ReadyIdleFSM
from QGCR.states.ready.ready_substate import ReadySubState


class TestReadyIdleFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 1
        self.fsm = ReadyIdleFSM(self.model)

    def test_enter_pushes_status(self):
        # on_update() ruft _on_enter() beim ersten Tick automatisch auf
        self.fsm.on_update()

        self.assertIn(("status", "Ready: Idle"), self.model.gui_items())

    def test_idle_stays_idle(self):
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_IDLE)

    def test_takeoff_event_transitions_to_takeoff(self):
        self.model.hfsm_events.append("TAKEOFF")
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_TAKEOFF)

    def test_heartbeat_lost_transitions_to_heartbeat_lost(self):
        self.model.px4_connected = False
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_HEARTBEAT_LOST)

    def test_no_heartbeat_yet_stays_idle(self):
        self.model.px4_connected = False
        self.model.px4_heartbeat_count = 0
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_IDLE)

    def test_mission_loaded_transitions_to_mission(self):
        self.model.mission_loaded = True
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_MISSION)

    def test_tab_mission_event_transitions_to_mission(self):
        self.model.hfsm_events.append("GUI_TAB_MISSION")
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_MISSION)

    def test_unknown_event_stays_idle(self):
        self.model.hfsm_events.append("FOO")
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_IDLE)


if __name__ == "__main__":
    unittest.main()
