# === PFAD-B FULL FILE: QGCR/test/test_gui_controller.py ===

import unittest

from QGCR.view.gui_controller import GUIController
from QGCR.view.button_policy import ButtonPolicy
from QGCR.model.model import Model


# ------------------------------------------------------------
# Dummy FSM für Controller-Tests
# ------------------------------------------------------------
class DummyFSM:
    def __init__(self):
        self.received_events = []

    def on_event(self, event):
        self.received_events.append(event)


# ------------------------------------------------------------
# Dummy Dispatcher
# ------------------------------------------------------------
class DummyDispatcher:
    def dispatch(self, *args, **kwargs):
        pass


# ------------------------------------------------------------
# Dummy GUI (implementiert IGUI minimal)
# ------------------------------------------------------------
class DummyGUI:
    def __init__(self):
        self.status_updates = []
        self.log_updates = []
        self.mission_items = []
        self.telemetry_updates = []
        self.button_state = None

    def set_button_state(self, mapping):
        self.button_state = mapping

    def update_status(self, text):
        self.status_updates.append(text)

    def update_log(self, text):
        self.log_updates.append(text)

    def update_mission_items(self, item):
        self.mission_items.append(item)

    def update_telemetry(self, telemetry_dict):
        self.telemetry_updates.append(telemetry_dict)


class TestGUIController(unittest.TestCase):

    def setUp(self):
        self.model = Model()
        self.fsm = DummyFSM()
        self.dispatcher = DummyDispatcher()
        self.gui = DummyGUI()
        self.policy = ButtonPolicy()

        self.controller = GUIController(
            model=self.model,
            fsm=self.fsm,
            dispatcher=self.dispatcher,
            gui=self.gui,
            button_policy=self.policy
        )

    # ------------------------------------------------------------
    # Test: Controller sendet Events an FSM
    # ------------------------------------------------------------
    def test_fsm_event_upload(self):
        self.controller.request_mission_upload()
        self.assertIn("MISSION_UPLOAD_REQUEST", self.fsm.received_events)

    def test_fsm_event_download(self):
        self.controller.request_mission_download()
        self.assertIn("MISSION_DOWNLOAD_REQUEST", self.fsm.received_events)

    def test_fsm_event_takeoff(self):
        self.controller.request_takeoff()
        self.assertIn("TAKEOFF_REQUEST", self.fsm.received_events)

    def test_fsm_event_land(self):
        self.controller.request_land()
        self.assertIn("LAND_REQUEST", self.fsm.received_events)

    def test_fsm_event_arm(self):
        self.controller.request_arm()
        self.assertIn("ARM_REQUEST", self.fsm.received_events)

    def test_fsm_event_disarm(self):
        self.controller.request_disarm()
        self.assertIn("DISARM_REQUEST", self.fsm.received_events)

    # ------------------------------------------------------------
    # Test: Model → Controller → GUI Status Update
    # ------------------------------------------------------------
    def test_status_update_flow(self):
        self.model.update_status("PX4 connected")
        self.assertIn("PX4 connected", self.gui.status_updates)

    # ------------------------------------------------------------
    # Test: Controller → GUI Log Update
    # ------------------------------------------------------------
    def test_log_update_flow(self):
        self.controller.on_log_update("Test log")
        self.assertIn("Test log", self.gui.log_updates)

    # ------------------------------------------------------------
    # Test: Controller → GUI Mission Item Update
    # ------------------------------------------------------------
    def test_mission_item_flow(self):
        self.controller.on_mission_item_update("WP1")
        self.assertIn("WP1", self.gui.mission_items)
