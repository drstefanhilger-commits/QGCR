# === PFAD-B FULL FILE: QGCR/test/unittest/test_integration_tab_router_mainwindow.py ===

import unittest
import tkinter as tk
from unittest.mock import MagicMock

from QGCR.view.main_window import MainWindow
from QGCR.view.tab_router import TabRouter


class TestIntegrationTabRouterMainWindow(unittest.TestCase):
    """
    MainWindow baut Home/Mission/Log + StatusBar und meldet Tab-Wechsel an den Controller
    (on_tab_changed → model.active_tab).
    Der TabRouter löst nichts aus.
    """

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.ctrl = MagicMock()
        self.gui = MainWindow(self.root, self.ctrl)
        self.gui.update()

    def tearDown(self):
        self.gui.destroy()
        self.root.destroy()

    def select_tab(self, tab_text):
        notebook = self.gui.notebook
        for tab_id in notebook.tabs():
            if notebook.tab(tab_id, "text") == tab_text:
                notebook.select(tab_id)
                break
        self.gui.update()
        return notebook.nametowidget(notebook.select())

    def test_tabs_present(self):
        texts = [self.gui.notebook.tab(t, "text") for t in self.gui.notebook.tabs()]
        self.assertEqual(texts, ["Home", "Mission", "Log"])

    def test_switch_to_mission(self):
        self.assertIs(self.select_tab("Mission"), self.gui.mission_tab)

    def test_switch_to_log(self):
        self.assertIs(self.select_tab("Log"), self.gui.log_tab)

    def test_switch_back_to_home(self):
        self.select_tab("Log")
        self.assertIs(self.select_tab("Home"), self.gui.home_tab)

    def test_status_bar_present(self):
        self.assertIs(self.gui.status_bar.controller, self.ctrl)

    def test_tab_router_has_no_side_effects(self):
        self.ctrl.reset_mock()
        router = TabRouter(self.ctrl)
        router.on_tab_changed("Mission")
        self.assertEqual(self.ctrl.method_calls, [])

    def test_tab_change_notifies_controller(self):
        for tab in ("Mission", "Log", "Home"):
            with self.subTest(tab=tab):
                self.ctrl.reset_mock()
                self.select_tab(tab)
                self.ctrl.on_tab_changed.assert_called_once_with(tab)

if __name__ == "__main__":
    unittest.main()
