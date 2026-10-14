# === PFAD-B FULL FILE: QGCR/test/unittest/test_model_mission_parser.py ===

import os
import unittest
from unittest.mock import patch

from pymavlink import mavutil

from QGCR.model.mission_parser import load_qgc_plan
from QGCR.test.unittest.plan_fixture import write_plan, WAYPOINTS


class TestModelMissionParser(unittest.TestCase):

    def setUp(self):
        self.path = write_plan()

    def tearDown(self):
        os.remove(self.path)

    @patch("builtins.print")
    def test_load_simple_items(self, _print):
        items = load_qgc_plan(self.path)

        self.assertEqual([i.seq for i in items], [0, 1, 2])
        for item, (lat, lon, alt) in zip(items, WAYPOINTS):
            self.assertEqual(item.get_type(), "MISSION_ITEM_INT")
            self.assertEqual(item.command, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT)
            self.assertEqual(item.frame, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT)
            self.assertEqual(item.x, int(lat * 1e7))
            self.assertEqual(item.y, int(lon * 1e7))
            self.assertAlmostEqual(item.z, alt)

    @patch("builtins.print")
    def test_null_params_become_zero(self, _print):
        self.assertEqual(load_qgc_plan(self.path)[0].param4, 0.0)

    def test_invalid_file_raises(self):
        with open(self.path, "w") as f:
            f.write("{kein json")
        with self.assertRaises(ValueError):
            load_qgc_plan(self.path)


if __name__ == "__main__":
    unittest.main()
