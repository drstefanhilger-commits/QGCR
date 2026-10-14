# === PFAD-B FULL FILE: QGCR/test/unittest/test_model_mavlink_commands.py ===

import math
import unittest

from pymavlink import mavutil

from QGCR.model.mavlink_commands import cmd_arm, cmd_disarm, cmd_land, cmd_mission_start


class TestModelMavlinkCommands(unittest.TestCase):

    def test_land_at_current_position(self):
        msg = cmd_land(1, 1)

        self.assertEqual(msg.command, mavutil.mavlink.MAV_CMD_NAV_LAND)
        self.assertEqual((msg.target_system, msg.target_component), (1, 1))
        for p in (msg.param4, msg.param5, msg.param6, msg.param7):
            self.assertTrue(math.isnan(p))

    def test_land_encodes(self):
        """NaN-Parameter lassen sich als MAVLink-Paket kodieren."""
        mav = mavutil.mavlink.MAVLink(None, srcSystem=255, srcComponent=0)
        self.assertGreater(len(cmd_land(1, 1).pack(mav)), 0)

    def test_mission_start(self):
        msg = cmd_mission_start(1, 1)

        self.assertEqual(msg.command, mavutil.mavlink.MAV_CMD_MISSION_START)
        self.assertEqual((msg.param1, msg.param2), (0, 0))
        self.assertEqual(cmd_mission_start(1, 1, first_item=3).param1, 3)

    def test_arm_disarm(self):
        self.assertEqual(cmd_arm().param1, 1)
        self.assertEqual(cmd_disarm().param1, 0)


if __name__ == "__main__":
    unittest.main()
