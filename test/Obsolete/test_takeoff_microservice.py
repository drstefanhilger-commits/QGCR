# === PFAD-B FULL FILE: tests/test_takeoff_microservice.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.services.takeoff_microservice import TakeoffMicroService


# ------------------------------------------------------------
# Hilfs-Mock für MAVLink Connection
# ------------------------------------------------------------
class MockMaster:
    def __init__(self):
        self.mav = MagicMock()
        self.set_mode = MagicMock()
        self._heartbeat = None
        self._global_pos = None

    def recv_match(self, type=None, blocking=False):
        if type == "HEARTBEAT":
            return self._heartbeat
        if type == "GLOBAL_POSITION_INT":
            return self._global_pos
        return None


class MockConnection:
    def __init__(self):
        self.master = MockMaster()
        self.target_system = 1
        self.target_component = 1


# ------------------------------------------------------------
# Test TakeoffMicroService
# ------------------------------------------------------------
class TestTakeoffMicroService(unittest.TestCase):

    def setUp(self):
        self.conn = MockConnection()
        self.ms = TakeoffMicroService(self.conn, target_altitude=10.0)

    # ------------------------------------------------------------
    # Start
    # ------------------------------------------------------------
    def test_start_initializes_state(self):
        self.ms.start()

        self.assertTrue(self.ms.started)
        self.assertFalse(self.ms.done)
        self.assertIsNone(self.ms.error)
        self.assertFalse(self.ms._arm_sent)
        self.assertFalse(self.ms._mode_sent)
        self.assertFalse(self.ms._takeoff_sent)

    # ------------------------------------------------------------
    # Arm senden
    # ------------------------------------------------------------
    def test_tick_sends_arm_first(self):
        self.ms.start()
        self.ms.tick()

        self.conn.master.mav.command_long_send.assert_called_once()
        self.assertTrue(self.ms._arm_sent)

    # ------------------------------------------------------------
    # Arm wiederholen, wenn nicht armed
    # ------------------------------------------------------------
    def test_tick_retries_arm_if_not_armed(self):
        self.ms.start()

        # HEARTBEAT ohne ARM-Flag
        hb = MagicMock()
        hb.base_mode = 0
        self.conn.master._heartbeat = hb

        self.ms.tick()  # send arm
        self.ms.tick()  # retry arm

        self.assertEqual(self.conn.master.mav.command_long_send.call_count, 2)

    # ------------------------------------------------------------
    # Mode setzen nach erfolgreichem Arm
    # ------------------------------------------------------------
    def test_tick_sets_mode_after_arm(self):
        self.ms.start()

        # HEARTBEAT mit ARM-Flag
        hb = MagicMock()
        hb.base_mode = 128  # MAV_MODE_FLAG_SAFETY_ARMED
        self.conn.master._heartbeat = hb

        self.ms._arm_sent = True  # simulate arm already sent

        self.ms.tick()

        self.conn.master.set_mode.assert_called_once_with("AUTO.TAKEOFF")
        self.assertTrue(self.ms._mode_sent)

    # ------------------------------------------------------------
    # Takeoff senden nach Mode
    # ------------------------------------------------------------
    def test_tick_sends_takeoff_after_mode(self):
        self.ms.start()

        hb = MagicMock()
        hb.base_mode = 128
        self.conn.master._heartbeat = hb

        self.ms._arm_sent = True
        self.ms._mode_sent = True

        self.ms.tick()

        self.conn.master.mav.command_long_send.assert_called()
        self.assertTrue(self.ms._takeoff_sent)

    # ------------------------------------------------------------
    # Takeoff bestätigt
    # ------------------------------------------------------------
    def test_tick_confirms_takeoff(self):
        self.ms.start()

        hb = MagicMock()
        hb.base_mode = 128
        self.conn.master._heartbeat = hb

        self.ms._arm_sent = True
        self.ms._mode_sent = True
        self.ms._takeoff_sent = True

        # GLOBAL_POSITION_INT mit Höhe > 0.5 m
        pos = MagicMock()
        pos.relative_alt = 600  # > 500
        self.conn.master._global_pos = pos

        self.ms.tick()

        self.assertTrue(self.ms.done)

    # ------------------------------------------------------------
    # Keine Bestätigung → nicht done
    # ------------------------------------------------------------
    def test_tick_not_done_if_no_altitude(self):
        self.ms.start()

        hb = MagicMock()
        hb.base_mode = 128
        self.conn.master._heartbeat = hb

        self.ms._arm_sent = True
        self.ms._mode_sent = True
        self.ms._takeoff_sent = True

        # Keine Höhe
        self.conn.master._global_pos = None

        self.ms.tick()

        self.assertFalse(self.ms.done)


if __name__ == "__main__":
    unittest.main()
