# === PFAD-B FULL FILE: test_airborne_takeoff_fsm.py ===

import unittest

from QGCR.states.airborne.subfsms.airborne_takeoff_fsm import AirborneTakeoffFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState
from QGCR.states.airborne.airborne_events import AirborneEvents


class DummyModel:
    pass


class TestAirborneTakeoffFSM(unittest.TestCase):

    def setUp(self):
        self.fsm = AirborneTakeoffFSM(DummyModel())

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_TAKEOFF)

    def test_no_event_stays_in_takeoff(self):
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_TAKEOFF)

    def test_takeoff_complete_switches_to_mission(self):
        self.fsm.handle_event(AirborneEvents.TAKEOFF_COMPLETE)
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_MISSION)


if __name__ == "__main__":
    unittest.main()
