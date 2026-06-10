# === PFAD-B FULL FILE: test_ready_mission_fsm.py ===

import unittest

from QGCR.test.dummy_model import DummyModel
from QGCR.states.ready.ready_mission_fsm import ReadyMissionFSM
from QGCR.states.ready_substate import ReadySubState


class TestReadyMissionFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = ReadyMissionFSM(self.model)

    def test_enter_generates_gui_event(self):
        # erster Tick → _on_enter()
        self.fsm.on_update()

        gui_events = list(self.model.queue_gui.queue)
        self.assertIn("MISSION_REQUESTED", gui_events)

    def test_stays_in_mission_state(self):
        # mehrfaches on_update() darf den Substate nicht ändern
        state1 = self.fsm.on_update()
        state2 = self.fsm.on_update()

        self.assertEqual(state1, ReadySubState.READY_MISSION)
        self.assertEqual(state2, ReadySubState.READY_MISSION)


if __name__ == "__main__":
    unittest.main()
