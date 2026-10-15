# === PFAD-B FULL FILE: QGCR/test/unittest/test_view_plot_2d.py ===

import tkinter as tk
import unittest

from QGCR.view.plot_2d import Plot2D


START = (47.397742, 8.545594)
NORTH_100M = (47.397742 + 100 / 111_320.0, 8.545594)
EAST_100M = (47.397742, 8.545594 + 100 / (111_320.0 * 0.6757))


class TestViewPlot2D(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.plot = Plot2D(self.root, width=600, height=400)
        self.plot.pack()
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def data(self, **kw):
        d = {"track": [], "waypoints": [], "start": None, "landing": None, "vehicle": None}
        d.update(kw)
        return d

    def tagged(self, tag):
        return self.plot.find_withtag(tag)

    def centre(self, tag):
        x0, y0, x1, y1 = self.plot.bbox(self.plot.find_withtag(tag)[0])
        return (x0 + x1) / 2, (y0 + y1) / 2

    def test_placeholder_without_data(self):
        self.plot.draw(self.data())
        self.assertTrue(self.tagged("placeholder"))

    def test_draws_track_start_landing_vehicle(self):
        self.plot.draw(self.data(track=[START, NORTH_100M, EAST_100M], start=START,
                                 landing=EAST_100M, vehicle=NORTH_100M,
                                 waypoints=[START, NORTH_100M]))

        for tag in ("track", "start", "landing", "vehicle", "waypoints", "scale", "north"):
            with self.subTest(tag=tag):
                self.assertTrue(self.tagged(tag))
        self.assertFalse(self.tagged("placeholder"))

    def test_north_is_up_and_east_is_right(self):
        self.plot.draw(self.data(start=START, vehicle=NORTH_100M, landing=EAST_100M))

        sx, sy = self.centre("start")
        vx, vy = self.centre("vehicle")
        lx, ly = self.centre("landing")
        self.assertLess(vy, sy)                     # Norden oben
        self.assertGreater(lx, sx)                  # Osten rechts

    def test_equal_scale_in_both_axes(self):
        self.plot.draw(self.data(start=START, vehicle=NORTH_100M, landing=EAST_100M))

        sx, sy = self.centre("start")
        vx, vy = self.centre("vehicle")
        lx, ly = self.centre("landing")
        self.assertAlmostEqual(sy - vy, lx - sx, delta=6)   # je 100 m

    def test_no_redraw_for_same_data(self):
        d = self.data(track=[START, NORTH_100M], start=START)
        self.plot.draw(d)
        items = self.plot.find_all()

        self.plot.draw(dict(d))
        self.assertEqual(self.plot.find_all(), items)

    def test_scale_bar_label(self):
        self.plot.draw(self.data(start=START, vehicle=NORTH_100M))
        labels = [self.plot.itemcget(i, "text") for i in self.tagged("scale")
                  if self.plot.type(i) == "text"]
        self.assertEqual(len(labels), 1)
        self.assertRegex(labels[0], r"^\d+ m$|^\d+(\.\d+)? km$")


if __name__ == "__main__":
    unittest.main()
