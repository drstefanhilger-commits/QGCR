# === PFAD-B FULL FILE: test_airborne_exit_fsm.py ===

import unittest

from QGCR.states.airborne.subfsms.airborne_exit_fsm import AirborneExitFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class DummyModel:
    pass


class TestAirborneExitFSM(unittest.TestCase):

    def setUp(self):
        self.fsm = AirborneExitFSM(DummyModel())

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_EXIT)

    def test_stays_in_exit(self):
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_EXIT)


if __name__ == "__main__":
    unittest.main()
