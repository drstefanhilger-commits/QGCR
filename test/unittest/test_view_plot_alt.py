# === PFAD-B FULL FILE: QGCR/test/unittest/test_view_plot_alt.py ===

import tkinter as tk
import unittest

from QGCR.view.plot_alt import AltitudePlot


class TestViewPlotAlt(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.plot = AltitudePlot(self.root, width=600, height=170)
        self.plot.pack()
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def texts(self, tag):
        return [self.plot.itemcget(i, "text") for i in self.plot.find_withtag(tag)]

    def test_placeholder_without_samples(self):
        self.plot.draw({"samples": []})
        self.assertTrue(self.plot.find_withtag("placeholder"))

        self.plot.draw({"samples": [(0.0, 1.0)]})          # ein Punkt reicht nicht
        self.assertTrue(self.plot.find_withtag("placeholder"))

    def test_draws_curve_axes_and_current_value(self):
        self.plot.draw({"samples": [(0, 0), (10, 10), (20, 20), (60, 0.2)]})

        for tag in ("altitude", "axis", "ytick", "xtick", "label", "current"):
            with self.subTest(tag=tag):
                self.assertTrue(self.plot.find_withtag(tag))
        self.assertEqual(self.texts("current"), ["0.2 m"])
        self.assertIn("20", self.texts("ytick"))
        self.assertIn("60", self.texts("xtick"))

    def test_higher_altitude_is_higher_on_screen(self):
        self.plot.draw({"samples": [(0, 0), (10, 20)]})
        coords = self.plot.coords(self.plot.find_withtag("altitude")[0])
        (xa, ya), (xb, yb) = coords[:2], coords[2:4]
        self.assertGreater(xb, xa)                          # Zeit nach rechts
        self.assertLess(yb, ya)                             # Höhe nach oben

    def test_no_redraw_for_same_data(self):
        self.plot.draw({"samples": [(0, 0), (5, 5)]})
        items = self.plot.find_all()
        self.plot.draw({"samples": [(0, 0), (5, 5)]})
        self.assertEqual(self.plot.find_all(), items)

    def test_nice_step(self):
        self.assertEqual(AltitudePlot.nice_step(20, 4), 5)
        self.assertEqual(AltitudePlot.nice_step(95, 6), 20)
        self.assertEqual(AltitudePlot.nice_step(3, 6), 0.5)


if __name__ == "__main__":
    unittest.main()
