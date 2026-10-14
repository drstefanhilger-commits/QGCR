# === PFAD-B FULL FILE: QGCR/test/unittest/test_connection_model_heartbeat.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.fake_mavlink import make_msg, run_connection


class TestConnectionModelHeartbeat(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.dispatcher = MagicMock()

    def test_heartbeat_pushes_telemetry_to_gui(self):
        hb = make_msg("HEARTBEAT", base_mode=128, custom_mode=3 << 24, system_status=4)
        run_connection(self.model, self.dispatcher, [hb])

        telemetry = [p for k, p in self.model.gui_items() if k == "telemetry"]
        self.assertEqual(telemetry[-1]["mode"], "POSCTL")
        self.assertTrue(telemetry[-1]["armed"])
        self.assertEqual(telemetry[-1]["px4_hb"], 1)
        self.assertTrue(telemetry[-1]["px4_connected"])

    def test_global_position_updates_model(self):
        pos = make_msg("GLOBAL_POSITION_INT", lat=473977418, lon=85455939, relative_alt=12500)
        run_connection(self.model, self.dispatcher, [pos])

        self.assertAlmostEqual(self.model.vehicle_lat, 47.3977418)
        self.assertAlmostEqual(self.model.vehicle_lon, 8.5455939)
        self.assertAlmostEqual(self.model.vehicle_alt, 12.5)
        self.dispatcher.dispatch.assert_not_called()

    def test_home_position_updates_model(self):
        home = make_msg("HOME_POSITION", latitude=473977418, longitude=85455939, altitude=488000)
        run_connection(self.model, self.dispatcher, [home])

        self.assertAlmostEqual(self.model.home_lat, 47.3977418)
        self.assertAlmostEqual(self.model.home_lon, 8.5455939)
        self.assertAlmostEqual(self.model.home_alt, 488.0)
        self.assertIn(("status", "Home set: 47.39774, 8.54559, 488.0 m"), self.model.gui_items())


if __name__ == "__main__":
    unittest.main()
