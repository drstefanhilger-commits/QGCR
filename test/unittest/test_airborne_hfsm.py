# === PFAD-B FULL FILE: QGCR/test/unittest/test_airborne_hfsm.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM
from QGCR.states.main_state import MainState


class TestAirborneHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True

        self.takeoff = MagicMock()
        self.takeoff.STATE_IDLE = "IDLE"
        self.takeoff.state = "IDLE"
        self.model.takeoff = self.takeoff

        self.fsm = AirborneHFSM(self.model)

    def test_enter_sets_state_and_starts_takeoff(self):
        state = self.fsm.on_update()

        self.assertEqual(state, MainState.AIRBORNE)
        self.assertEqual(self.model.hfsm_main, "AIRBORNE")
        self.assertEqual(self.model.hfsm_sub, "FLIGHT")
        self.takeoff.start.assert_called_once()

    def test_enter_does_not_restart_running_takeoff(self):
        self.takeoff.state = "WAIT_CLIMB"
        self.fsm.on_update()

        self.takeoff.start.assert_not_called()

    def test_stays_airborne_and_ticks_takeoff(self):
        self.fsm.on_update()
        state = self.fsm.on_update()

        self.assertEqual(state, MainState.AIRBORNE)
        self.assertEqual(self.takeoff.tick.call_count, 2)

    def test_reset_event_goes_reset(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_connection_lost_goes_reset(self):
        self.fsm.on_update()
        self.model.px4_connected = False

        self.assertEqual(self.fsm.on_update(), MainState.RESET)


if __name__ == "__main__":
    unittest.main()
