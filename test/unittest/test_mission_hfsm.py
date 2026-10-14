# === PFAD-B FULL FILE: QGCR/test/unittest/test_mission_hfsm.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.mission.mission_hfsm import MissionHFSM
from QGCR.states.main_state import MainState


class TestMissionHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.fsm = MissionHFSM(self.model)

    def test_enter_sets_state(self):
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)
        self.assertEqual(self.model.hfsm_main, "MISSION")
        self.assertEqual(self.model.hfsm_sub, "IDLE")

    def test_back_events_go_ready(self):
        for event in ("BACK", "MISSION_BACK", "EV_GOTO_READY"):
            with self.subTest(event=event):
                fsm = MissionHFSM(self.model)
                fsm.on_update()
                self.model.hfsm_events.append(event)

                self.assertEqual(fsm.on_update(), MainState.READY)

    def test_reset_event_goes_reset(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")
        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_other_events_stay_mission(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("MISSION_UPLOAD")
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

    def test_connection_lost_goes_reset(self):
        self.fsm.on_update()
        self.model.px4_connected = False
        self.assertEqual(self.fsm.on_update(), MainState.RESET)


if __name__ == "__main__":
    unittest.main()
