import unittest
import tkinter as tk

from QGCR.view.telemetry_view import TelemetryView


class TestViewTelemetryView(unittest.TestCase):
    """
    Unit-Test für die modularisierte TelemetryView.
    Testet:
    - Initialzustand
    - update()
    - clear()
    """

    def setUp(self):
        # Headless Tk-Root
        self.root = tk.Tk()
        self.root.withdraw()

        # TelemetryView instanziieren
        self.view = TelemetryView(self.root)
        self.root.update()

    def tearDown(self):
        self.view.destroy()
        self.root.destroy()

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------
    def test_initial_state(self):
        """Alle Felder müssen initial auf Default stehen."""
        self.assertEqual(self.view.var_mode.get(), "UNKNOWN")
        self.assertEqual(self.view.var_armed.get(), "False")
        self.assertEqual(self.view.var_alt.get(), "0.0")
        self.assertEqual(self.view.var_px4_hb.get(), "-")
        self.assertEqual(self.view.var_gui_spinner.get(), "-")

    def test_update_sets_all_fields(self):
        """update() setzt alle Felder korrekt."""
        telemetry = {
            "mode": "OFFBOARD",
            "armed": True,
            "alt": 42.7,
            "px4_hb": 123,
            "gui_spinner": 7,
        }

        self.view.update(telemetry)
        self.root.update()

        self.assertEqual(self.view.var_mode.get(), "OFFBOARD")
        self.assertEqual(self.view.var_armed.get(), "True")
        self.assertEqual(self.view.var_alt.get(), "42.7")
        self.assertEqual(self.view.var_px4_hb.get(), "123")
        self.assertEqual(self.view.var_gui_spinner.get(), "7")

    def test_clear_resets_all_fields(self):
        """clear() setzt alle Felder zurück."""
        self.view.update({
            "mode": "AUTO",
            "armed": True,
            "alt": 99.9,
            "px4_hb": 55,
            "gui_spinner": 3,
        })
        self.root.update()

        self.view.clear()
        self.root.update()

        self.assertEqual(self.view.var_mode.get(), "UNKNOWN")
        self.assertEqual(self.view.var_armed.get(), "False")
        self.assertEqual(self.view.var_alt.get(), "0.0")
        self.assertEqual(self.view.var_px4_hb.get(), "-")
        self.assertEqual(self.view.var_gui_spinner.get(), "-")


if __name__ == "__main__":
    unittest.main()
