# test_heartbeat_monitor.py

import unittest
from types import SimpleNamespace
from pymavlink.dialects.v20 import common as mavlink

from QGCR.communication.heartbeat_monitor import HeartbeatMonitor


def make_hb(msg_type, base_mode=0):
    """
    Erzeugt ein Fake-Heartbeat-Objekt.
    """
    ns = SimpleNamespace()
    ns.type = msg_type
    ns.base_mode = base_mode
    ns.get_msgId = lambda: mavlink.MAVLINK_MSG_ID_HEARTBEAT
    return ns


class TestHeartbeatMonitor(unittest.TestCase):

    def setUp(self):
        # Timeout bewusst klein für Tests
        self.monitor = HeartbeatMonitor(timeout_s=1.0)

    def test_px4_heartbeat_updates_state(self):
        hb = make_hb(mavlink.MAV_TYPE_QUADROTOR, base_mode=81)
        self.monitor.handle_heartbeat(hb, source="px4")

        self.assertIsNotNone(self.monitor.last_px4_hb)
        self.assertEqual(self.monitor.last_px4_hb.base_mode, 81)

    def test_gcs_heartbeat_updates_state(self):
        hb = make_hb(mavlink.MAV_TYPE_GCS)
        self.monitor.handle_heartbeat(hb, source="gcs")

        self.assertIsNotNone(self.monitor.last_gcs_hb)

    def test_px4_lost_event(self):
        hb = make_hb(mavlink.MAV_TYPE_QUADROTOR)
        self.monitor.handle_heartbeat(hb, source="px4")

        # Zeit simulieren → Timeout überschreiten
        self.monitor._last_px4_ts -= 2.0

        events = self.monitor.update()
        self.assertIn("PX4_LOST", events)

    def test_px4_recovered_event(self):
        # 1) PX4 war verloren
        self.monitor._last_px4_ts = None
        self.monitor._px4_alive = False

        # 2) Jetzt kommt wieder ein Heartbeat
        hb = make_hb(mavlink.MAV_TYPE_QUADROTOR)
        self.monitor.handle_heartbeat(hb, source="px4")

        events = self.monitor.update()
        self.assertIn("PX4_RECOVERED", events)

    def test_px4_reboot_detected(self):
        # 1) alter Heartbeat
        old = make_hb(mavlink.MAV_TYPE_QUADROTOR, base_mode=81)
        self.monitor.handle_heartbeat(old, source="px4")

        # 2) neuer Heartbeat mit anderem base_mode → reboot
        new = make_hb(mavlink.MAV_TYPE_QUADROTOR, base_mode=0)
        self.monitor.handle_heartbeat(new, source="px4")

        events = self.monitor.update()
        self.assertIn("PX4_REBOOTED", events)

    def test_gcs_lost_and_recovered(self):
        hb = make_hb(mavlink.MAV_TYPE_GCS)
        self.monitor.handle_heartbeat(hb, source="gcs")

        # Timeout simulieren
        self.monitor._last_gcs_ts -= 2.0
        events = self.monitor.update()
        self.assertIn("GCS_LOST", events)

        # Wieder Heartbeat
        hb2 = make_hb(mavlink.MAV_TYPE_GCS)
        self.monitor.handle_heartbeat(hb2, source="gcs")
        events = self.monitor.update()
        self.assertIn("GCS_RECOVERED", events)

    def test_real_px4_mavlink_heartbeat_is_accepted(self):
        """
        Verifiziert, dass der HeartbeatMonitor einen echten MAVLink-Heartbeat
        (PX4, MAVLink v2) korrekt verarbeitet.
        """
        hb = mavlink.MAVLink_heartbeat_message(
            type=mavlink.MAV_TYPE_QUADROTOR,
            autopilot=mavlink.MAV_AUTOPILOT_PX4,
            base_mode=mavlink.MAV_MODE_FLAG_SAFETY_ARMED,
            custom_mode=3,
            system_status=mavlink.MAV_STATE_ACTIVE,
            mavlink_version=3,  # MAVLink 2.0
        )

        self.monitor.handle_heartbeat(hb, source="px4")

        self.assertIsNotNone(self.monitor.last_px4_hb)
        self.assertEqual(self.monitor.last_px4_hb.type, mavlink.MAV_TYPE_QUADROTOR)
        self.assertEqual(self.monitor.last_px4_hb.autopilot, mavlink.MAV_AUTOPILOT_PX4)
        self.assertEqual(self.monitor.last_px4_hb.base_mode, mavlink.MAV_MODE_FLAG_SAFETY_ARMED)




if __name__ == "__main__":
    unittest.main()
