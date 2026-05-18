# === PFAD-B FULL FILE: test_airborne_lost_fsm.py ===

import unittest

from QGCR.states.airborne.subfsms.airborne_lost_fsm import AirborneLostFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState


class DummyModel:
    pass


class TestAirborneLostFSM(unittest.TestCase):

    def setUp(self):
        self.fsm = AirborneLostFSM(DummyModel())

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_LOST)

    def test_stays_in_lost(self):
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_LOST)


if __name__ == "__main__":
    unittest.main()
