# === PFAD-B FULL FILE: QGCR/test/unittest/test_startup_home_fsm.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.startup.subfsms.startup_home_fsm import StartupHomeFSM
from QGCR.states.startup.startup_substate import StartupSubState


class TestStartupHomeFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 1
        self.fsm = StartupHomeFSM(self.model)

    def set_home(self):
        self.model.home_lat = 47.3977418
        self.model.home_lon = 8.5455939
        self.model.home_alt = 488.0

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, StartupSubState.STARTUP_HOME)

    def test_waits_for_home(self):
        self.assertEqual(self.fsm.on_update(), StartupSubState.STARTUP_HOME)
        self.assertEqual(self.model.qgcr_logs(), [])

    def test_home_received_goes_to_mission(self):
        self.set_home()

        self.assertEqual(self.fsm.on_update(), StartupSubState.STARTUP_MISSION)
        self.assertIn(("status", "Startup: Home-Position empfangen"), self.model.gui_items())

    def test_home_is_logged_once(self):
        self.fsm.on_update()
        self.set_home()
        self.fsm.on_update()

        home_logs = [l for l in self.model.qgcr_logs() if "Home set" in l]
        self.assertEqual(home_logs, ["[QGCR] Home set: 47.39774, 8.54559, 488.0 m"])

    def test_heartbeat_lost_goes_back_to_heartbeat(self):
        self.model.px4_connected = False
        self.set_home()

        self.assertEqual(self.fsm.on_update(), StartupSubState.STARTUP_HEARTBEAT)
        self.assertIn("[QGCR] [STARTUP_HOME] Heartbeat verloren → STARTUP_HEARTBEAT", self.model.qgcr_logs())
        self.assertIn(("status", "Startup: Home-Schritt abgebrochen (Heartbeat verloren)"), self.model.gui_items())


if __name__ == "__main__":
    unittest.main()
