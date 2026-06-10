import unittest
import tkinter as tk

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


if __name__ == "__main__":
    unittest.main()
