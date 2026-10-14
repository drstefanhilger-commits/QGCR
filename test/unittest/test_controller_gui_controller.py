# === PFAD-B FULL FILE: QGCR/test/unittest/test_controller_gui_controller.py ===

import unittest
from unittest.mock import patch

from QGCR.controller.gui_controller import GUIController
from QGCR.test.unittest.dummy_model import DummyModel


class TestControllerGUIController(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.gui = GUIController(self.model, None, None, self.model.queue_registry)

    @patch("builtins.print")
    def test_home_tab_buttons_reach_hfsm_queue(self, _print):
        for event in ("ARM", "DISARM", "TAKEOFF", "LAND", "RESET"):
            self.gui.handle_button_event(event)

        self.assertEqual(list(self.model.hfsm_events),
                         ["ARM", "DISARM", "TAKEOFF", "LAND", "RESET"])

    @patch("builtins.print")
    def test_unknown_button_event_is_ignored(self, _print):
        self.gui.handle_button_event("ARMM")
        self.assertEqual(len(self.model.hfsm_events), 0)

    def test_tab_mission_only_from_ready(self):
        for state, expected in (("READY", ["EV_GOTO_MISSION"]), ("STARTUP", []),
                                ("AIRBORNE", []), ("MISSION", [])):
            with self.subTest(state=state):
                self.model.hfsm_events.clear()
                self.model.hfsm_main = state
                self.gui.on_tab_mission()
                self.assertEqual(list(self.model.hfsm_events), expected)

    def test_tab_home_only_from_mission(self):
        for state, expected in (("MISSION", ["EV_GOTO_READY"]), ("READY", []),
                                ("STARTUP", []), ("AIRBORNE", [])):
            with self.subTest(state=state):
                self.model.hfsm_events.clear()
                self.model.hfsm_main = state
                self.gui.on_tab_home()
                self.assertEqual(list(self.model.hfsm_events), expected)

    def test_tab_changed_sets_active_tab(self):
        self.gui.on_tab_changed("Log")
        self.assertEqual(self.model.active_tab, "Log")


if __name__ == "__main__":
    unittest.main()
