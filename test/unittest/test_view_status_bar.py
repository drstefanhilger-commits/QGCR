import unittest
import tkinter as tk

from QGCR.view.status_bar import StatusBar


class TestViewStatusBar(unittest.TestCase):
    """
    Unit-Test für die modularisierte StatusBar.
    Testet ausschließlich:
    - Initialisierung
    - set_status()
    - get_status()
    """

    def setUp(self):
        # Headless Tk-Root erzeugen
        self.root = tk.Tk()
        self.root.withdraw()  # Kein Fenster anzeigen

        # StatusBar instanziieren
        self.bar = StatusBar(self.root)

        # Tk aktualisieren, damit Widgets existieren
        self.root.update()

    def tearDown(self):
        self.bar.destroy()
        self.root.destroy()

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------
    def test_initial_state(self):
        """Statusbar startet mit 'Bereit'."""
        self.assertEqual(self.bar.get_status(), "Bereit")

    def test_set_status(self):
        """set_status() aktualisiert den Text korrekt."""
        self.bar.set_status("PX4 verbunden")
        self.root.update()

        self.assertEqual(self.bar.get_status(), "PX4 verbunden")

    def test_multiple_updates(self):
        """Mehrere Updates überschreiben den Status korrekt."""
        self.bar.set_status("A")
        self.bar.set_status("B")
        self.bar.set_status("C")
        self.root.update()

        self.assertEqual(self.bar.get_status(), "C")


if __name__ == "__main__":
    unittest.main()
