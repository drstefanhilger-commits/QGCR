# === PFAD-B FULL FILE: QGCR/test/test_integration_gui_controller.py ===

import unittest

from QGCR.view.gui_controller import GUIController
from QGCR.view.button_policy import ButtonPolicy
from QGCR.states.main_state import MainState
from QGCR.model.model import Model


# ------------------------------------------------------------
# Dummy FSM für Integrationstest
# ------------------------------------------------------------
class DummyFSM:
    def __init__(self):
        self.received = []

    def on_event(self, event):
        self.received.append(event)


# ------------------------------------------------------------
# Dummy GUI implementiert IGUI
# ------------------------------------------------------------
class DummyGUI:
    def __init__(self):
        self.button_state = None
        self.status_updates = []
        self.log_updates = []
        self.mission_items = []
        self.telemetry_updates = []

    def set_button_state(self, mapping: dict):
        self.button_state = mapping

    def update_status(self, text: str):
        self.status_updates.append(text)

    def update_log(self, text: str):
        self.log_updates.append(text)

    def update_mission_items(self, item):
        self.mission_items.append(item)

    def update_telemetry(self, telemetry_dict):
        self.telemetry_updates.append(telemetry_dict)


class TestIntegrationGUIController(unittest.TestCase):

    def setUp(self):
        self.model = Model()
        self.fsm = DummyFSM()
        self.gui = DummyGUI()
        self.policy = ButtonPolicy()

        # Neuer refaktorisierter Controller
        self.controller = GUIController(
            model=self.model,
            fsm=self.fsm,
            dispatcher=None,
            gui=self.gui,
            button_policy=self.policy
        )

    # ------------------------------------------------------------
    # Model → Controller → GUI
    # ------------------------------------------------------------
    def test_status_flow(self):
        self.model.update_status("PX4 connected")
        self.assertEqual(self.gui.status_updates, ["PX4 connected"])

    def test_log_flow(self):
        self.model.log_callback("Hello Log")
        self.assertEqual(self.gui.log_updates, ["Hello Log"])

    def test_mission_item_flow(self):
        self.model.mission_item_callback("WP1")
        self.assertEqual(self.gui.mission_items, ["WP1"])

    def test_telemetry_flow(self):
        telemetry = {"mode": "AUTO", "armed": True, "alt": 12.3}
        self.model.telemetry_callback(telemetry)
        self.assertEqual(self.gui.telemetry_updates, [telemetry])

    # ------------------------------------------------------------
    # GUI → Controller → FSM
    # ------------------------------------------------------------
    def test_fsm_takeoff(self):
        self.controller.request_takeoff()
        self.assertEqual(self.fsm.received, ["TAKEOFF_REQUEST"])

    def test_fsm_land(self):
        self.controller.request_land()
        self.assertEqual(self.fsm.received, ["LAND_REQUEST"])

    def test_fsm_arm(self):
        self.controller.request_arm()
        self.assertEqual(self.fsm.received, ["ARM_REQUEST"])

    def test_fsm_disarm(self):
        self.controller.request_disarm()
        self.assertEqual(self.fsm.received, ["DISARM_REQUEST"])

    def test_fsm_upload(self):
        self.controller.request_mission_upload()
        self.assertEqual(self.fsm.received, ["MISSION_UPLOAD_REQUEST"])

    def test_fsm_download(self):
        self.controller.request_mission_download()
        self.assertEqual(self.fsm.received, ["MISSION_DOWNLOAD_REQUEST"])

    # ------------------------------------------------------------
    # State → Controller → GUI (ButtonPolicy)
    # ------------------------------------------------------------
    def test_button_policy_startup(self):
        self.controller.update_buttons(MainState.STARTUP)
        expected = self.policy.for_state(MainState.STARTUP)
        self.assertEqual(self.gui.button_state, expected)

    def test_button_policy_ready(self):
        self.controller.update_buttons(MainState.READY)
        expected = self.policy.for_state(MainState.READY)
        self.assertEqual(self.gui.button_state, expected)

    def test_button_policy_airborne(self):
        self.controller.update_buttons(MainState.AIRBORNE)
        expected = self.policy.for_state(MainState.AIRBORNE)
        self.assertEqual(self.gui.button_state, expected)


if __name__ == "__main__":
    unittest.main()
