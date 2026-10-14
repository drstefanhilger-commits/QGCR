# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_connection.py ===

import unittest

from pymavlink import mavutil

from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl, gcs_link, wait_for


@requires_sitl
class TestPX4Connection(unittest.TestCase):
    """
    PX4-SITL sendet auf Port #0 (18570 → 14550) Heartbeats an die GCS.
    """

    def setUp(self):
        self.sitl = PX4Sitl()
        self.sitl.start()
        self.mav = gcs_link()

    def tearDown(self):
        self.mav.close()
        self.sitl.stop()

    def test_px4_heartbeat_on_gcs_port(self):
        hb = wait_for(self.mav, "HEARTBEAT", timeout=90)

        self.assertIsNotNone(hb, "Kein PX4 HEARTBEAT auf udp:0.0.0.0:14550")
        self.assertEqual(hb.get_srcSystem(), 1)
        self.assertEqual(hb.autopilot, mavutil.mavlink.MAV_AUTOPILOT_PX4)
        self.assertEqual(hb.type, mavutil.mavlink.MAV_TYPE_FIXED_WING)


if __name__ == "__main__":
    unittest.main()
