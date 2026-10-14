# === PFAD-B FULL FILE: QGCR/test/unittest/test_ready_heartbeat_lost_fsm.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.ready.subfsms.ready_heartbeat_lost_fsm import ReadyHeartbeatLostFSM
from QGCR.states.ready.ready_substate import ReadySubState


class TestReadyHeartbeatLostFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = ReadyHeartbeatLostFSM(self.model)

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, ReadySubState.READY_HEARTBEAT_LOST)

    def test_enter_shows_error_and_disables_buttons(self):
        self.fsm.on_update()
        items = self.model.gui_items()

        self.assertIn(("status", "FEHLER: PX4 Heartbeat verloren!"), items)
        self.assertIn(("log", "READY_HEARTBEAT_LOST: Heartbeat lost"), items)
        self.assertIn(("disable", "takeoff"), items)
        self.assertIn(("disable", "land"), items)

    def test_stays_in_heartbeat_lost(self):
        self.assertEqual(self.fsm.on_update(), ReadySubState.READY_HEARTBEAT_LOST)

        # Keine automatische Erholung, auch nicht bei neuem Heartbeat
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 5
        self.assertEqual(self.fsm.on_update(), ReadySubState.READY_HEARTBEAT_LOST)

    def test_gui_events_are_consumed(self):
        self.model.gui_events.append("GUI_TAB_HOME")
        state = self.fsm.on_update()

        self.assertEqual(state, ReadySubState.READY_HEARTBEAT_LOST)
        self.assertEqual(len(self.model.gui_events), 0)


if __name__ == "__main__":
    unittest.main()
