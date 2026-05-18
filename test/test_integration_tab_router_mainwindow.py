# === PFAD-B FULL FILE: QGCR/test/test_integration_tab_router_mainwindow.py ===

import unittest
import tkinter as tk

from QGCR.view.main_window import MainWindow


# ------------------------------------------------------------
# Dummy Controller für Integrationstest
# ------------------------------------------------------------
class DummyController:
    def __init__(self):
        self.called = []

    # GUI callbacks (werden vom MainWindow gesetzt)
    def request_takeoff(self): pass
    def request_land(self): pass
    def request_arm(self): pass
    def request_disarm(self): pass
    def request_mission_upload(self): pass
    def request_mission_download(self): pass


# ------------------------------------------------------------
# Dummy TabRouter, der nur protokolliert
# ------------------------------------------------------------
class DummyTabRouter:
    def __init__(self):
        self.events = []

    def on_tab_changed(self, tab_name):
        self.events.append(tab_name)


class TestIntegrationTabRouterMainWindow(unittest.TestCase):

    def setUp(self):
        # Headless Tk
        self.root = tk.Tk()
        self.root.withdraw()

        # Dummy Controller
        self.ctrl = DummyController()

        # Dummy TabRouter
        self.router = DummyTabRouter()

        # MainWindow instanziieren
        self.gui = MainWindow(self.ctrl)

        # TabRouter ersetzen
        self.gui.tab_router = self.router

        self.gui.update()

        # Initiales Event ignorieren
        self.router.events.clear()

    def tearDown(self):
        self.gui.destroy()
        self.root.destroy()

    # ------------------------------------------------------------
    # Hilfsfunktion: Tab wechseln
    # ------------------------------------------------------------
    def select_tab(self, tab_text):
        notebook = self.gui.notebook

        for i in range(len(notebook.tabs())):
            if notebook.tab(i, "text") == tab_text:
                notebook.select(i)
                break

        notebook.event_generate("<<NotebookTabChanged>>")
        self.gui.update_idletasks()

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------
    def test_switch_to_mission(self):
        self.select_tab("Mission")
        self.assertEqual(self.router.events, ["Mission"])

    def test_switch_to_home(self):
        self.select_tab("Home")
        self.assertEqual(self.router.events, ["Home"])

    def test_switch_to_log(self):
        self.select_tab("Log")
        self.assertEqual(self.router.events, ["Log"])

    def test_switch_to_capabilities(self):
        self.select_tab("Capabilities")
        self.assertEqual(self.router.events, ["Capabilities"])


if __name__ == "__main__":
    unittest.main()
