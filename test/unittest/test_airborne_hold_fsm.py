# === PFAD-B FULL FILE: test_airborne_hold_fsm.py ===

import unittest

from QGCR.states.airborne.subfsms.airborne_hold_fsm import AirborneHoldFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState
from QGCR.states.airborne.airborne_events import AirborneEvents


class DummyModel:
    pass


class TestAirborneHoldFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = AirborneHoldFSM(self.model)

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_HOLD)

    def test_no_event_keeps_hold(self):
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_HOLD)

    def test_mode_auto_mission_switches_to_mission(self):
        self.fsm.handle_event(AirborneEvents.MODE_AUTO_MISSION)
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_MISSION)

    def test_mission_started_switches_to_mission(self):
        self.fsm.handle_event(AirborneEvents.MISSION_STARTED)
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_MISSION)

    def test_rtl_does_not_change_state(self):
        self.fsm.handle_event(AirborneEvents.MODE_AUTO_RTL)
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_HOLD)

    def test_land_does_not_change_state(self):
        self.fsm.handle_event(AirborneEvents.MODE_AUTO_LAND)
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_HOLD)

    def test_event_queue_order(self):
        # 1: RTL (ignoriert), 2: MISSION_STARTED (→ MISSION)
        self.fsm.handle_event(AirborneEvents.MODE_AUTO_RTL)
        self.fsm.handle_event(AirborneEvents.MISSION_STARTED)

        # Erstes on_update: RTL wird verarbeitet → bleibt HOLD
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_HOLD)

        # Zweites on_update: MISSION_STARTED → MISSION
        self.fsm.on_update()
        self.assertEqual(self.fsm.state_enum, AirborneSubState.AIRBORNE_MISSION)


if __name__ == "__main__":
    unittest.main()
