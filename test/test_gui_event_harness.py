# === PFAD-B FULL FILE: QGCR/test/test_gui_event_harness.py ===

import unittest
import tkinter as tk

from QGCR.core.queue_registry import QueueRegistry
from QGCR.view.gui_event_loop import GUIEventLoop
from QGCR.view.gui_controller import GUIController


class DummyGUI:
    def __init__(self):
        self.status_updates = []
        self.log_updates = []
        self.telemetry_updates = []
        self.mission_items = []
        self.button_states = []

    def update_status(self, text):
        self.status_updates.append(text)

    def update_log(self, text):
        self.log_updates.append(text)

    def update_telemetry(self, data):
        self.telemetry_updates.append(data)

    def update_mission_items(self, item):
        self.mission_items.append(item)

    def set_button_state(self, mapping):
        self.button_states.append(mapping)


class DummyFSM: pass
class DummyDispatcher: pass


class TestGUIEventHarness(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.registry = QueueRegistry()
        self.gui = DummyGUI()

        self.controller = GUIController(
            model=None,
            fsm=DummyFSM(),
            dispatcher=DummyDispatcher(),
            gui=self.gui,
            button_policy=None
        )

        self.loop = GUIEventLoop(
            root=self.root,
            controller=self.controller,
            gui_event_queue=self.registry.gui,
            interval_ms=1000  # irrelevant, wir nutzen poll_once()
        )

    def tearDown(self):
        self.root.destroy()

    def test_status_event(self):
        self.registry.gui.push(("status", "PX4 connected"))
        self.loop.poll_once()
        self.assertEqual(self.gui.status_updates, ["PX4 connected"])

    def test_log_event(self):
        self.registry.gui.push(("log", "Mission uploaded"))
        self.loop.poll_once()
        self.assertEqual(self.gui.log_updates, ["Mission uploaded"])

    def test_telemetry_event(self):
        data = {"alt": 42}
        self.registry.gui.push(("telemetry", data))
        self.loop.poll_once()
        self.assertEqual(self.gui.telemetry_updates, [data])

    def test_mission_item_event(self):
        self.registry.gui.push(("mission_item", "WP1"))
        self.loop.poll_once()
        self.assertEqual(self.gui.mission_items, ["WP1"])

    def test_button_state_event(self):
        mapping = {"takeoff": "normal", "land": "disabled"}
        self.registry.gui.push(("buttons", mapping))
        self.loop.poll_once()
        self.assertEqual(self.gui.button_states, [mapping])


if __name__ == "__main__":
    unittest.main()
