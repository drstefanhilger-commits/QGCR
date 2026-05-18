# === PFAD-B FULL FILE: QGCR/test/test_gui_buttons.py ===

import unittest
import tkinter as tk

from QGCR.view.main_window import MainWindow
from QGCR.view.gui_controller import GUIController
from QGCR.view.button_policy import ButtonPolicy
from QGCR.model.model import Model
from QGCR.states.main_state import MainState
from QGCR.states.main_state_machine import MainStateMachine


class TestGUIButtons(unittest.TestCase):

    def setUp(self):
        # Headless Tk
        self.root = tk.Tk()
        self.root.withdraw()

        self.model = Model()
        self.sm = MainStateMachine(self.model)
        self.policy = ButtonPolicy()

        # Controller zuerst erzeugen (GUI wird später gesetzt)
        self.controller = GUIController(
            model=self.model,
            fsm=self.sm,
            dispatcher=None,
            gui=None,               # wird später gesetzt
            button_policy=self.policy
        )

        # GUI erzeugen
        self.gui = MainWindow(self.controller)

        # Controller bekommt echte GUI
        self.controller.gui = self.gui

        self.gui.update()

    def tearDown(self):
        self.gui.destroy()
        self.root.destroy()

    # Hilfsfunktion für saubere Vergleiche
    def state(self, widget):
        return str(widget["state"])

    # ------------------------------------------------------------
    # STARTUP
    # ------------------------------------------------------------
    def test_buttons_in_startup(self):
        self.gui.update_state(MainState.STARTUP)

        self.assertEqual(self.state(self.gui.button_bar.btn_takeoff), "disabled")
        self.assertEqual(self.state(self.gui.button_bar.btn_land), "disabled")
        self.assertEqual(self.state(self.gui.button_bar.btn_arm), "disabled")
        self.assertEqual(self.state(self.gui.button_bar.btn_disarm), "disabled")

        self.assertEqual(self.state(self.gui.mission_tab.btn_upload), "disabled")
        self.assertEqual(self.state(self.gui.mission_tab.btn_download), "disabled")

    # ------------------------------------------------------------
    # READY
    # ------------------------------------------------------------
    def test_buttons_in_ready(self):
        self.gui.update_state(MainState.READY)

        self.assertEqual(self.state(self.gui.button_bar.btn_takeoff), "normal")
        self.assertEqual(self.state(self.gui.button_bar.btn_land), "disabled")
        self.assertEqual(self.state(self.gui.button_bar.btn_arm), "normal")
        self.assertEqual(self.state(self.gui.button_bar.btn_disarm), "normal")

        self.assertEqual(self.state(self.gui.mission_tab.btn_upload), "normal")
        self.assertEqual(self.state(self.gui.mission_tab.btn_download), "normal")

    # ------------------------------------------------------------
    # AIRBORNE
    # ------------------------------------------------------------
    def test_buttons_in_airborne(self):
        self.gui.update_state(MainState.AIRBORNE)

        self.assertEqual(self.state(self.gui.button_bar.btn_takeoff), "disabled")
        self.assertEqual(self.state(self.gui.button_bar.btn_land), "normal")
        self.assertEqual(self.state(self.gui.button_bar.btn_arm), "disabled")
        self.assertEqual(self.state(self.gui.button_bar.btn_disarm), "disabled")

        self.assertEqual(self.state(self.gui.mission_tab.btn_upload), "disabled")
        self.assertEqual(self.state(self.gui.mission_tab.btn_download), "disabled")
