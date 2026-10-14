# === PFAD-B FULL FILE: QGCR/test/unittest/test_ready_takeoff_fsm.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.ready.subfsms.ready_takeoff_fsm import ReadyTakeoffFSM
from QGCR.states.ready.ready_substate import ReadySubState


class TestReadyTakeoffFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True

        self.ms = MagicMock()
        self.ms.done = False
        self.ms.error = None
        self.model.services.takeoff = self.ms

        self.fsm = ReadyTakeoffFSM(self.model)

    def test_enter_starts_microservice(self):
        self.fsm.on_update()

        self.ms.start.assert_called_once()
        self.assertIn(("status", "Takeoff initiated"), self.model.gui_items())

    def test_stays_in_takeoff_while_running(self):
        state1 = self.fsm.on_update()
        state2 = self.fsm.on_update()

        self.assertEqual(state1, ReadySubState.READY_TAKEOFF)
        self.assertEqual(state2, ReadySubState.READY_TAKEOFF)
        self.assertEqual(self.ms.tick.call_count, 2)
        self.ms.start.assert_called_once()

    def test_done_returns_to_idle(self):
        self.ms.done = True
        state = self.fsm.on_update()

        self.assertEqual(state, ReadySubState.READY_IDLE)
        self.assertIn(("status", "Takeoff complete"), self.model.gui_items())

    def test_error_returns_to_idle(self):
        self.ms.error = "ARM timeout"
        state = self.fsm.on_update()

        self.assertEqual(state, ReadySubState.READY_IDLE)
        self.assertIn(("status", "Takeoff FAILED: ARM timeout"), self.model.gui_items())

    def test_tab_home_aborts_takeoff(self):
        self.model.gui_events.append("GUI_TAB_HOME")
        state = self.fsm.on_update()

        self.assertEqual(state, ReadySubState.READY_IDLE)
        self.ms.tick.assert_not_called()
        self.assertIn(("status", "Takeoff aborted"), self.model.gui_items())


if __name__ == "__main__":
    unittest.main()
