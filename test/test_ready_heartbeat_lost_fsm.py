# === PFAD-B FULL FILE: test_ready_heartbeat_lost_fsm.py ===

import unittest

from QGCR.test.dummy_model import DummyModel
from QGCR.states.ready.ready_heartbeat_lost_fsm import ReadyHeartbeatLostFSM
from QGCR.states.ready_substate import ReadySubState


class TestReadyHeartbeatLostFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = ReadyHeartbeatLostFSM(self.model)

    def test_enter_generates_gui_event(self):
        # erster Tick → _on_enter()
        self.fsm.on_update()

        gui_events = list(self.model.queue_gui.queue)
        self.assertIn("PX4_LOST", gui_events)

    def test_stays_in_heartbeat_lost_state(self):
        # mehrfaches on_update() darf den Substate nicht ändern
        state1 = self.fsm.on_update()
        state2 = self.fsm.on_update()

        self.assertEqual(state1, ReadySubState.READY_HEARTBEAT_LOST)
        self.assertEqual(state2, ReadySubState.READY_HEARTBEAT_LOST)


if __name__ == "__main__":
    unittest.main()
