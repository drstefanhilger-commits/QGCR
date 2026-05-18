import unittest
import tkinter as tk

from QGCR.view.log_tab import LogTab


class TestViewLogTab(unittest.TestCase):
    """
    Unit-Test für den modularisierten LogTab.
    Testet ausschließlich:
    - Initialisierung
    - append_log()
    - Inhalt des Text-Widgets
    """

    def setUp(self):
        # Headless Tk-Root erzeugen
        self.root = tk.Tk()
        self.root.withdraw()  # Kein Fenster anzeigen

        # LogTab instanziieren
        self.tab = LogTab(self.root)

        # Tk aktualisieren, damit Widgets existieren
        self.root.update()

    def tearDown(self):
        self.tab.destroy()
        self.root.destroy()

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------
    def test_initial_state(self):
        """Text-Widget muss leer sein."""
        content = self.tab.text_widget.get("1.0", tk.END).strip()
        self.assertEqual(content, "")

    def test_append_single_line(self):
        """append_log() fügt eine Zeile hinzu."""
        self.tab.append_log("Hello World")
        self.root.update()

        content = self.tab.text_widget.get("1.0", tk.END).strip()
        self.assertEqual(content, "Hello World")

    def test_append_multiple_lines(self):
        """Mehrere append_log()-Aufrufe hängen korrekt an."""
        self.tab.append_log("Line 1")
        self.tab.append_log("Line 2")
        self.tab.append_log("Line 3")
        self.root.update()

        content = self.tab.text_widget.get("1.0", tk.END).strip()
        self.assertEqual(content, "Line 1\nLine 2\nLine 3")

    def test_widget_is_readonly(self):
        """Das Text-Widget muss nach append_log() wieder disabled sein."""
        self.tab.append_log("Test")
        self.root.update()

        state = str(self.tab.text_widget["state"])
        self.assertEqual(state, "disabled")


if __name__ == "__main__":
    unittest.main()
