# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_home_position.py ===

import time
import unittest

from pymavlink import mavutil

from QGCR.test.unittest.sitl_helper import (
    PX4Sitl, requires_sitl, gcs_link, wait_for, send_gcs_heartbeat,
)


@requires_sitl
class TestPX4HomePosition(unittest.TestCase):

    def setUp(self):
        self.sitl = PX4Sitl()
        self.sitl.start()
        self.mav = gcs_link()

    def tearDown(self):
        self.mav.close()
        self.sitl.stop()

    def test_home_position_request(self):
        hb = wait_for(self.mav, "HEARTBEAT", timeout=90)
        self.assertIsNotNone(hb, "Kein PX4 HEARTBEAT empfangen")

        # Home wird erst nach GPS-Fix gesetzt → mehrfach anfragen
        home = None
        deadline = time.time() + 60
        while home is None and time.time() < deadline:
            send_gcs_heartbeat(self.mav)
            self.mav.mav.command_long_send(
                hb.get_srcSystem(), hb.get_srcComponent(),
                mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
                0,
                mavutil.mavlink.MAVLINK_MSG_ID_HOME_POSITION,
                0, 0, 0, 0, 0, 0,
            )
            home = wait_for(self.mav, "HOME_POSITION", timeout=1.0)

        self.assertIsNotNone(home, "HOME_POSITION wurde nicht empfangen")
        self.assertNotEqual(home.latitude, 0)
        self.assertNotEqual(home.longitude, 0)


if __name__ == "__main__":
    unittest.main()
