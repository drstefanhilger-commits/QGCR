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


if __name__ == "__main__":
    unittest.main()
