#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock
from QGCR.test.harness.mission_microservice import MissionMicroService
from QGCR.test.utils.mission_item_builder import make_waypoint


class TestMissionMicroService(unittest.TestCase):

    def test_upload_sequence(self):
        # Fake MAVLink mastermission_microservice
        master = MagicMock()
        master.recv_match = MagicMock()

        # Mission items
        mission = [
            make_waypoint(0, 47.0, 8.0, 10),
            make_waypoint(1, 47.1, 8.1, 20),
        ]

        # PX4 responses in order
        master.recv_match.side_effect = [
            # PX4 requests item 0
            MagicMock(get_type=lambda: "MISSION_REQUEST", seq=0),
            # PX4 requests item 1
            MagicMock(get_type=lambda: "MISSION_REQUEST", seq=1),
            # PX4 sends ACK
            MagicMock(get_type=lambda: "MISSION_ACK", type=0),
        ]

        ms = MissionMicroService(master, 1, 1)
        ms.upload(mission)

        # Check that MISSION_COUNT was sent
        master.mav.mission_count_send.assert_called_with(1, 1, 2)

        # Check that two mission items were sent
        self.assertEqual(master.mav.mission_item_int_send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
