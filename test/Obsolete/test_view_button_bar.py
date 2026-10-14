import unittest
import tkinter as tk

from QGCR.view.button_bar import ButtonBar


class DummyController:
    """
    Minimaler Dummy, um Callback-Aufrufe zu zählen.
    """
    def __init__(self):
        self.takeoff_called = 0
        self.land_called = 0
        self.arm_called = 0
        self.disarm_called = 0

    def takeoff(self):
        self.takeoff_called += 1

    def land(self):
        self.land_called += 1

    def arm(self):
        self.arm_called += 1

    def disarm(self):
        self.disarm_called += 1


class TestViewButtonBar(unittest.TestCase):
    """
    Unit-Test für die modularisierte ButtonBar.
    Testet:
    - Initialzustand (alle disabled)
    - set_enabled()
    - Callback-Aufrufe
    """

    def setUp(self):
        # Headless Tk-Root
        self.root = tk.Tk()
        self.root.withdraw()

        # Dummy-Controller
        self.ctrl = DummyController()

        # ButtonBar instanziieren
        self.bar = ButtonBar(
            self.root,
            on_takeoff=self.ctrl.takeoff,
            on_land=self.ctrl.land,
            on_arm=self.ctrl.arm,
            on_disarm=self.ctrl.disarm,
        )

        self.root.update()

    def tearDown(self):
        self.bar.destroy()
        self.root.destroy()

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------
    def test_initial_state_all_disabled(self):
        """Alle Buttons müssen initial disabled sein."""
        self.assertEqual(str(self.bar.btn_takeoff["state"]), "disabled")
        self.assertEqual(str(self.bar.btn_land["state"]), "disabled")
        self.assertEqual(str(self.bar.btn_arm["state"]), "disabled")
        self.assertEqual(str(self.bar.btn_disarm["state"]), "disabled")

    def test_set_enabled(self):
        """set_enabled() aktiviert/deaktiviert Buttons korrekt."""
        self.bar.set_enabled({
            "takeoff": True,
            "land": False,
            "arm": True,
            "disarm": False
        })
        self.root.update()

        self.assertEqual(str(self.bar.btn_takeoff["state"]), "normal")
        self.assertEqual(str(self.bar.btn_land["state"]), "disabled")
        self.assertEqual(str(self.bar.btn_arm["state"]), "normal")
        self.assertEqual(str(self.bar.btn_disarm["state"]), "disabled")

    def test_callbacks_are_called(self):
        """Button-Klicks rufen die übergebenen Callbacks auf."""
        # Buttons aktivieren
        self.bar.set_enabled({
            "takeoff": True,
            "land": True,
            "arm": True,
            "disarm": True
        })
        self.root.update()

        # Klicks simulieren
        self.bar.btn_takeoff.invoke()
        self.bar.btn_land.invoke()
        self.bar.btn_arm.invoke()
        self.bar.btn_disarm.invoke()

        self.assertEqual(self.ctrl.takeoff_called, 1)
        self.assertEqual(self.ctrl.land_called, 1)
        self.assertEqual(self.ctrl.arm_called, 1)
        self.assertEqual(self.ctrl.disarm_called, 1)


if __name__ == "__main__":
    unittest.main()
