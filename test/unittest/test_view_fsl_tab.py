# === PFAD-B FULL FILE: QGCR/test/unittest/test_view_fsl_tab.py ===

import tkinter as tk
import unittest
from unittest.mock import MagicMock

from QGCR.view.fsl_tab import FslTab


class TestViewFslTab(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.ctrl = MagicMock()
        self.tab = FslTab(self.root, controller=self.ctrl)
        self.tab.pack()
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_default_values(self):
        v = self.tab.values()
        self.assertEqual(v["drone_id"], "T1")
        self.assertEqual((v["east"], v["north"], v["up"]), ("-150", "100", "20"))
        self.assertEqual((v["speed"], v["timeout"], v["battery_min"]), ("8", "180", "30"))

    def test_trigger_button_sends_values(self):
        self.tab.vars["east"].set(" -200 ")
        self.tab.btn_trigger.invoke()
        values = self.ctrl.send_trigger.call_args[0][0]
        self.assertEqual(values["east"], "-200")

    def test_abort_button(self):
        self.tab.set_enabled(trigger=False, abort=True, model_hint=False)
        self.tab.btn_abort.invoke()
        self.ctrl.abort_intercept.assert_called_once_with()

    def test_set_enabled_and_model_hint(self):
        self.tab.set_enabled(trigger=False, abort=False, model_hint=True)
        self.root.update()
        self.assertEqual(str(self.tab.btn_trigger["state"]), "disabled")
        self.assertEqual(self.tab.btn_model.winfo_manager(), "pack")

        self.tab.btn_model.invoke()
        self.ctrl.switch_to_fsl_model.assert_called_once_with()

        self.tab.set_enabled(trigger=True, abort=False, model_hint=False)
        self.root.update()
        self.assertEqual(self.tab.btn_model.winfo_manager(), "")

    def test_show_status(self):
        self.tab.show_status("INTERCEPT/FLIGHT", "FSL fliegt", "Wartepunkt …", "Akku: 80 %")
        self.assertEqual(self.tab.lbl_state["text"], "Zustand: INTERCEPT/FLIGHT")
        self.assertEqual(self.tab.lbl_status["text"], "FSL fliegt")

    def test_has_plots(self):
        self.assertTrue(hasattr(self.tab.plot, "draw"))
        self.assertTrue(hasattr(self.tab.alt_plot, "draw"))


if __name__ == "__main__":
    unittest.main()
