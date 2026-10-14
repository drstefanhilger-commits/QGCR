# === PFAD-B FULL FILE: QGCR/test/unittest/test_view_log_tab.py ===

import unittest
import tkinter as tk

from QGCR.view.log_tab import LogTab


class TestViewLogTab(unittest.TestCase):
    """
    Unit-Test für den LogTab mit drei Log-Fenstern (PX4 / Simulator / QGCR).
    """

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.tab = LogTab(self.root)
        self.root.update()

    def tearDown(self):
        self.tab.destroy()
        self.root.destroy()

    @staticmethod
    def _content(widget):
        return widget.get("1.0", tk.END).strip()

    def test_initial_state(self):
        for widget in (self.tab.px4_text, self.tab.sim_text, self.tab.qgcr_text):
            self.assertEqual(self._content(widget), "")

    def test_append_px4(self):
        self.tab.append_px4("[PX4-1] Ready")
        self.assertEqual(self._content(self.tab.px4_text), "[PX4-1] Ready")
        self.assertEqual(self._content(self.tab.qgcr_text), "")

    def test_append_sim(self):
        self.tab.append_sim("[SIM-gz] started")
        self.assertEqual(self._content(self.tab.sim_text), "[SIM-gz] started")

    def test_append_qgcr_multiple_lines(self):
        self.tab.append_qgcr("Line 1")
        self.tab.append_qgcr("Line 2")
        self.tab.append_qgcr("Line 3")

        self.assertEqual(self._content(self.tab.qgcr_text), "Line 1\nLine 2\nLine 3")


if __name__ == "__main__":
    unittest.main()
