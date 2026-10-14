# === PFAD-B FULL FILE: QGCR/test/unittest/test_view_status_bar.py ===

import unittest
import tkinter as tk

from QGCR.view.status_bar import StatusBar


class TestViewStatusBar(unittest.TestCase):
    """
    Unit-Test für die StatusBar (HFSM, Sub-State, Mode, Armed, HB, Spinner).
    """

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.bar = StatusBar(self.root, controller=None)
        self.root.update()

    def tearDown(self):
        self.bar.destroy()
        self.root.destroy()

    def text(self):
        return self.bar.status_var.get()

    def test_initial_state(self):
        self.assertEqual(
            self.text(),
            "HFSM: -    Sub: -    Mode: -    Armed: DISARMED    HB: 0    Spin: |",
        )

    def test_setters_update_text(self):
        self.bar.set_hfsm_state("READY")
        self.bar.set_sub_state("IDLE")
        self.bar.set_mode("AUTO")
        self.bar.set_armed(True)
        self.bar.set_hb(42)

        self.assertEqual(
            self.text(),
            "HFSM: READY    Sub: IDLE    Mode: AUTO    Armed: ARMED    HB: 42    Spin: |",
        )

    def test_message(self):
        self.assertEqual(self.bar.message_var.get(), "")

        self.bar.set_message("ACK: 400 → 0")

        self.assertEqual(self.bar.message_var.get(), "ACK: 400 → 0")
        self.assertTrue(self.text().startswith("HFSM: -"))   # Statuszeile unverändert

    def test_spinner_wraps_around(self):
        frames = []
        for _ in range(4):
            self.bar.spin()
            frames.append(self.text().rsplit(" ", 1)[-1])

        self.assertEqual(frames, ["/", "-", "\\", "|"])


if __name__ == "__main__":
    unittest.main()
