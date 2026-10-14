# === PFAD-B FULL FILE: QGCR/test/test_end_to_end_flow.py ===

import unittest
import tkinter as tk
from tkinter import ttk

from QGCR.view.main_window import MainWindow
from QGCR.view.gui_controller import GUIController
from QGCR.view.button_policy import ButtonPolicy
from QGCR.model.model import Model


# ------------------------------------------------------------
# Dummy FSM für End-to-End-Tests
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
# Hilfsfunktion: Button finden
# ------------------------------------------------------------
def find_button(root, text):
    for child in root.winfo_children():

        if isinstance(child, ttk.Button) and child.cget("text") == text:
            return child

        if isinstance(child, tk.Button) and child.cget("text") == text:
            return child

        found = find_button(child, text)
        if found:
            return found

    return None


class TestEndToEndFlow(unittest.TestCase):

    def setUp(self):
        self.model = Model()
        self.fsm = DummyFSM()
        self.dispatcher = DummyDispatcher()
        self.policy = ButtonPolicy()

        # 1. Controller zuerst erzeugen (mit Dummy-GUI Platzhalter)
        #    GUI wird später gesetzt
        self.gui_placeholder = None

        self.controller = GUIController(
            model=self.model,
            fsm=self.fsm,
            dispatcher=self.dispatcher,
            gui=self.gui_placeholder,   # wird überschrieben
            button_policy=self.policy
        )

        # 2. Jetzt MainWindow erzeugen, das IGUI implementiert
        self.gui = MainWindow(self.controller)

        # 3. Controller bekommt echte GUI
        self.controller.gui = self.gui

        self.gui.update()

    def tearDown(self):
        self.gui.destroy()

    # --------------------------------------------------------
    # GUI → Controller → FSM:
    # Klick auf "Upload" löst MISSION_UPLOAD_REQUEST aus
    # --------------------------------------------------------
    def test_upload_button_triggers_fsm_event(self):
        upload_button = find_button(self.gui, "Upload")

        self.assertIsNotNone(upload_button, "Upload Button nicht gefunden")

        upload_button.config(state="normal")
        upload_button.invoke()
        self.gui.update()

        self.assertIn(
            "MISSION_UPLOAD_REQUEST",
            self.fsm.received_events,
            "FSM hat kein MISSION_UPLOAD_REQUEST Event erhalten",
        )

    # --------------------------------------------------------
    # Model → Controller → GUI:
    # Statusbar-Update
    # --------------------------------------------------------
    def test_model_status_updates_statusbar(self):
        self.model.update_status("PX4 connected")
        self.gui.update_idletasks()

        self.assertEqual(
            self.gui.statusbar.get_status(),
            "PX4 connected",
            "Statusbar wurde nicht aktualisiert"
        )

    # --------------------------------------------------------
    # Verkabelung Model → Controller → GUI
    # --------------------------------------------------------
    def test_wiring_status_flow(self):
        # 1. Model → Controller
        self.assertIs(
            self.model.status_callback.__func__,
            self.controller.on_status_update.__func__,
        )

        # 2. Controller → GUI
        self.assertIs(
            self.controller.gui.update_status.__func__,
            self.gui.update_status.__func__,
        )

        # 3. Controller → GUI Instanz
        self.assertIs(
            self.controller.gui.update_status.__self__,
            self.gui,
        )

        # 4. End-to-end
        self.controller.on_status_update("PX4 connected")
        self.gui.update_idletasks()

        self.assertEqual(
            self.gui.statusbar.get_status(),
            "PX4 connected",
        )


if __name__ == "__main__":
    unittest.main()
