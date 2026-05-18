# === PFAD-B FULL FILE: test_ready_idle_fsm.py ===

import unittest

from QGCR.test.dummy_model import DummyModel
from QGCR.states.ready.ready_idle_fsm import ReadyIdleFSM
from QGCR.states.ready_substate import ReadySubState


class TestReadyIdleFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = ReadyIdleFSM(self.model)

    def test_enter_generates_gui_events(self):
        # on_update() ruft _on_enter() beim ersten Tick automatisch auf
        self.fsm.on_update()

        gui_events = list(self.model.queue_gui.queue)

        self.assertIn("ENABLE_TAKEOFF", gui_events)
        self.assertIn("ENABLE_MISSION", gui_events)
        self.assertIn("DISABLE_LAND", gui_events)
        self.assertIn("SHOW_READY_STATUS", gui_events)

    def test_idle_stays_idle(self):
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_IDLE)

    def test_takeoff_requested_transitions_to_takeoff(self):
        self.model.takeoff_requested = True
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_TAKEOFF)

    def test_mission_requested_transitions_to_mission(self):
        self.model.mission_requested = True
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_MISSION)

    def test_heartbeat_lost_transitions_to_lost(self):
        self.model.px4_heartbeat_ok = False
        state = self.fsm.on_update()
        self.assertEqual(state, ReadySubState.READY_HEARTBEAT_LOST)


if __name__ == "__main__":
    unittest.main()
