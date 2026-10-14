# === PFAD-B FULL FILE: QGCR/test/unittest/test_ready_hfsm.py ===

import unittest
from unittest.mock import MagicMock, patch

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.main_state import MainState


class TestReadyHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.model.takeoff = MagicMock()
        self.fsm = ReadyHFSM(self.model)

    def test_enter_sets_state_and_clears_events(self):
        self.model.hfsm_events.append("TAKEOFF")   # alter Event aus Vorzyklus

        state = self.fsm.on_update()

        self.assertEqual(state, MainState.READY)
        self.assertEqual(self.model.hfsm_main, "READY")
        self.assertEqual(self.model.hfsm_sub, "IDLE")
        self.assertEqual(len(self.model.hfsm_events), 0)

    def test_stays_ready_and_ticks_takeoff(self):
        self.fsm.on_update()
        state = self.fsm.on_update()

        self.assertEqual(state, MainState.READY)
        self.assertEqual(self.model.takeoff.tick.call_count, 2)

    def test_takeoff_event_goes_airborne(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("TAKEOFF")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)

    def test_reset_event_goes_reset(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_connection_lost_ignored_during_grace_phase(self):
        self.fsm.on_update()
        self.model.px4_connected = False

        self.assertEqual(self.fsm.on_update(), MainState.READY)

    def test_connection_lost_after_grace_phase_goes_reset(self):
        with patch("QGCR.states.ready.ready_hfsm.time.time", return_value=1000.0):
            self.fsm.on_update()

        self.model.px4_connected = False

        with patch("QGCR.states.ready.ready_hfsm.time.time", return_value=1006.0):
            self.assertEqual(self.fsm.on_update(), MainState.RESET)


if __name__ == "__main__":
    unittest.main()
