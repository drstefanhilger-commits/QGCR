import unittest
import tkinter as tk
from unittest.mock import MagicMock

from QGCR.view.home_tab import HomeTab


class TestViewHomeTab(unittest.TestCase):
    """
    Unit-Test für den modularisierten HomeTab.
    Testet:
    - Initialisierung
    - Canvas existiert
    - clear()
    - draw_text()
    """

    def setUp(self):
        # Headless Tk-Root
        self.root = tk.Tk()
        self.root.withdraw()

        # HomeTab instanziieren
        self.tab = HomeTab(self.root)

        # Tk aktualisieren, damit Widgets existieren
        self.root.update()

    def tearDown(self):
        self.tab.destroy()
        self.root.destroy()

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------
    def test_canvas_exists(self):
        """Canvas muss existieren."""
        self.assertIsNotNone(self.tab.canvas)
        self.assertIsInstance(self.tab.canvas, tk.Canvas)

    def test_initial_placeholder_text(self):
        """Der Platzhalter-Text muss beim Start existieren."""
        items = self.tab.canvas.find_all()
        self.assertGreater(len(items), 0)

    def test_clear_removes_all_items(self):
        """clear() löscht alle Canvas-Elemente."""
        self.tab.clear()
        self.root.update()

        items = self.tab.canvas.find_all()
        self.assertEqual(len(items), 0)

    def test_draw_text_adds_item(self):
        """draw_text() fügt ein Canvas-Element hinzu."""
        self.tab.clear()
        self.tab.draw_text(100, 200, "Hello")
        self.root.update()

        items = self.tab.canvas.find_all()
        self.assertEqual(len(items), 1)


class TestViewHomeTabModelSelector(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.ctrl = MagicMock()
        self.ctrl.get_model_choices.return_value = ["gz_rc_cessna", "gz_fsl_rocket_vtol"]
        self.ctrl.get_selected_model.return_value = "gz_rc_cessna"
        self.tab = HomeTab(self.root, controller=self.ctrl)

    def tearDown(self):
        self.tab.destroy()
        self.root.destroy()

    def test_shows_choices_and_current_model(self):
        self.assertEqual(list(self.tab.model_combo["values"]), ["gz_rc_cessna", "gz_fsl_rocket_vtol"])
        self.assertEqual(self.tab.model_var.get(), "gz_rc_cessna")
        self.assertEqual(str(self.tab.model_combo["state"]), "readonly")

    def test_selection_requests_model_change(self):
        self.tab.model_combo.current(1)
        self.tab.model_combo.event_generate("<<ComboboxSelected>>")
        self.root.update()

        self.ctrl.request_model_change.assert_called_once_with("gz_fsl_rocket_vtol")

    def test_clear_track_button(self):
        self.tab.clear_track_button.invoke()
        self.ctrl.clear_track.assert_called_once_with()

    def test_has_altitude_plot(self):
        from QGCR.view.plot_alt import AltitudePlot
        self.assertIsInstance(self.tab.alt_plot, AltitudePlot)

    def test_mission_button_sends_event(self):
        self.tab.mission_button.invoke()
        self.ctrl.handle_button_event.assert_called_once_with("MISSION_START")

    def test_set_model(self):
        self.tab.set_model("gz_fsl_rocket_vtol", enabled=False)

        self.assertEqual(self.tab.model_var.get(), "gz_fsl_rocket_vtol")
        self.assertEqual(str(self.tab.model_combo["state"]), "disabled")

        self.tab.set_model("gz_fsl_rocket_vtol", enabled=True)
        self.assertEqual(str(self.tab.model_combo["state"]), "readonly")


if __name__ == "__main__":
    unittest.main()
