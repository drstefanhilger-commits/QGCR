# === PFAD-B FULL FILE: QGCR/test/unittest/test_sim_gazebo_markers.py ===

import os
import tempfile
import threading
import time
import unittest

from QGCR.sim.gazebo_markers import GazeboMarkers


ORIGIN = GazeboMarkers.DEFAULT_ORIGIN
NORTH_10M = (ORIGIN[0] + 10 / 111_320.0, ORIGIN[1])


class FakeGz:
    """Zeichnet gz-Aufrufe auf; Ergebnis steuerbar."""

    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []
        self.event = threading.Event()

    def __call__(self, args):
        service = args[2].rsplit("/", 1)[-1]               # create / remove
        req = args[-1]
        name = req.split('name: "')[-1].split('"')[0]
        self.calls.append((service, name, req))
        self.event.set()
        return self.ok

    def ops(self):
        return [(s, n) for s, n, _ in self.calls]


class TestSimGazeboMarkers(unittest.TestCase):

    def setUp(self):
        self.gz = FakeGz()
        self.markers = GazeboMarkers(runner=self.gz)
        self.addCleanup(self.markers.stop)

    def settle(self, n_calls, timeout=2.0):
        deadline = time.time() + timeout
        while len(self.gz.calls) < n_calls and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)

    def test_enu_conversion(self):
        x, y = self.markers.to_enu(NORTH_10M)
        self.assertAlmostEqual(x, 0.0, places=3)
        self.assertAlmostEqual(y, 10.0, places=2)

        east = (ORIGIN[0], ORIGIN[1] + 10 / (111_320.0 * 0.6757))
        x, _ = self.markers.to_enu(east)
        self.assertAlmostEqual(x, 10.0, delta=0.05)

    def test_creates_start_and_landing(self):
        self.markers.request(ORIGIN, NORTH_10M)
        self.settle(2)

        self.assertEqual(self.gz.ops(), [("create", "qgcr_start"), ("create", "qgcr_landing")])
        start_req = self.gz.calls[0][2]
        landing_req = self.gz.calls[1][2]
        self.assertIn("<pose>0.00 0.00 0", start_req)
        self.assertIn("<pose>0.00 10.00 0", landing_req)
        self.assertIn("0 0.8 0 1", start_req)              # grün
        self.assertIn("0.9 0 0 1", landing_req)            # rot
        self.assertNotIn("<collision", start_req)          # rein visuell

    def test_same_request_does_nothing(self):
        self.markers.request(ORIGIN, None)
        self.settle(1)
        self.markers.request(ORIGIN, None)
        self.settle(2, timeout=0.3)

        self.assertEqual(self.gz.ops(), [("create", "qgcr_start")])

    def test_moved_marker_is_replaced(self):
        self.markers.request(ORIGIN, None)
        self.settle(1)
        self.markers.request(NORTH_10M, None)
        self.settle(3)

        self.assertEqual(self.gz.ops(), [("create", "qgcr_start"), ("remove", "qgcr_start"),
                                         ("create", "qgcr_start")])

    def test_marker_removed_when_none(self):
        self.markers.request(ORIGIN, NORTH_10M)
        self.settle(2)
        self.markers.request(ORIGIN, None)
        self.settle(3)

        self.assertEqual(self.gz.ops()[-1], ("remove", "qgcr_landing"))

    def test_invalidate_places_again(self):
        self.markers.request(ORIGIN, None)
        self.settle(1)
        self.markers.invalidate()                          # neue Gazebo-Instanz
        self.markers.request(ORIGIN, None)
        self.settle(2)

        self.assertEqual(self.gz.ops(), [("create", "qgcr_start"), ("create", "qgcr_start")])

    def test_failed_create_is_retried_after_interval(self):
        self.gz.ok = False
        self.markers.RETRY_INTERVAL = 0.2
        self.markers.request(ORIGIN, None)
        self.settle(1)

        self.markers.request(ORIGIN, None)                 # sofort: noch keine Wiederholung
        time.sleep(0.05)
        self.assertEqual(len(self.gz.calls), 1)

        self.gz.ok = True
        time.sleep(0.25)
        self.markers.request(ORIGIN, None)
        self.settle(2)
        self.assertEqual(self.gz.ops(), [("create", "qgcr_start"), ("create", "qgcr_start")])

    def test_request_does_not_block(self):
        slow = threading.Event()
        self.gz.ok = True
        original = self.markers._run
        self.markers._run = lambda args: (slow.wait(1.0), original(args))[1]

        start = time.time()
        self.markers.request(ORIGIN, NORTH_10M)
        self.assertLess(time.time() - start, 0.1)
        slow.set()

    def test_stop_ends_worker(self):
        self.markers.stop()
        self.assertFalse(self.markers._thread.is_alive())


class TestSimGazeboMarkersOrigin(unittest.TestCase):

    def test_origin_from_world_sdf(self):
        with tempfile.TemporaryDirectory() as px4:
            worlds = os.path.join(px4, "Tools", "simulation", "gz", "worlds")
            os.makedirs(worlds)
            with open(os.path.join(worlds, "default.sdf"), "w") as f:
                f.write("<spherical_coordinates><latitude_deg>48.1</latitude_deg>"
                        "<longitude_deg> 11.5 </longitude_deg></spherical_coordinates>")
            markers = GazeboMarkers(px4_dir=px4, runner=lambda a: True)
            markers.stop()

        self.assertEqual(markers.origin, (48.1, 11.5))

    def test_origin_fallback(self):
        markers = GazeboMarkers(px4_dir="/nicht/vorhanden", runner=lambda a: True)
        markers.stop()
        self.assertEqual(markers.origin, GazeboMarkers.DEFAULT_ORIGIN)


if __name__ == "__main__":
    unittest.main()
