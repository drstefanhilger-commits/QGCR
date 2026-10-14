# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_mission_download_harness.py ===

import unittest

from pymavlink import mavutil

from QGCR.test.unittest.sitl_helper import (
    PX4Sitl, requires_sitl, gcs_link, wait_for, send_gcs_heartbeat,
)


@requires_sitl
class TestPX4MissionDownload(unittest.TestCase):
    """
    Mission-Download-Protokoll über Port #0 gegen PX4-SITL.
    """

    def setUp(self):
        self.sitl = PX4Sitl()
        self.sitl.start()
        self.mav = gcs_link()

    def tearDown(self):
        self.mav.close()
        self.sitl.stop()

    def test_mission_download(self):
        hb = wait_for(self.mav, "HEARTBEAT", timeout=90)
        self.assertIsNotNone(hb, "Kein PX4 HEARTBEAT empfangen")

        tsys, tcomp = hb.get_srcSystem(), hb.get_srcComponent()

        # MISSION_REQUEST_LIST (bis MISSION_COUNT kommt)
        mission_count = None
        for _ in range(10):
            send_gcs_heartbeat(self.mav)
            self.mav.mav.mission_request_list_send(tsys, tcomp)
            msg = wait_for(self.mav, "MISSION_COUNT", timeout=1.0)
            if msg is not None:
                mission_count = msg.count
                break

        self.assertIsNotNone(mission_count, "MISSION_COUNT wurde nicht empfangen")

        items = {}
        for seq in range(mission_count):
            self.mav.mav.mission_request_int_send(tsys, tcomp, seq)
            msg = wait_for(self.mav, "MISSION_ITEM_INT", timeout=5.0)
            self.assertIsNotNone(msg, f"MISSION_ITEM_INT seq={seq} wurde nicht empfangen")
            items[msg.seq] = msg

        if mission_count > 0:
            self.mav.mav.mission_ack_send(tsys, tcomp, mavutil.mavlink.MAV_MISSION_ACCEPTED)

        self.assertEqual(len(items), mission_count)


if __name__ == "__main__":
    unittest.main()
