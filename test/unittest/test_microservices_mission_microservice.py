#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock
from QGCR.communication.microservices.mission_microservice import MissionMicroService


class TestMicroservicesMissionMicroservice(unittest.TestCase):

    def test_upload_sequence(self):
        master = MagicMock()
        master.recv_match = MagicMock()

        item0 = MagicMock(seq=0, frame=0, command=16, current=0,
                          autocontinue=1, param1=0, param2=0, param3=0,
                          param4=0, x=100000000, y=100000000, z=10)

        item1 = MagicMock(seq=1, frame=0, command=16, current=0,
                          autocontinue=1, param1=0, param2=0, param3=0,
                          param4=0, x=200000000, y=200000000, z=20)

        mission = [item0, item1]

        master.recv_match.side_effect = [
            MagicMock(get_type=lambda: "MISSION_REQUEST_INT", seq=0),
            MagicMock(get_type=lambda: "MISSION_REQUEST_INT", seq=1),
            MagicMock(get_type=lambda: "MISSION_ACK", type=0),
        ]

        ms = MissionMicroService(master, 1, 1)
        ms.upload(mission)

        master.mav.mission_count_send.assert_called_with(1, 1, 2)
        self.assertEqual(master.mav.mission_item_int_send.call_count, 2)

    def test_download_sequence(self):
        master = MagicMock()
        master.recv_match = MagicMock()

        mission_count_msg = MagicMock(count=2)
        mission_item0 = MagicMock(seq=0)
        mission_item1 = MagicMock(seq=1)

        master.recv_match.side_effect = [
            mission_count_msg,
            mission_item0,
            mission_item1,
        ]

        ms = MissionMicroService(master, 1, 1)
        mission = ms.download()

        self.assertEqual(len(mission), 2)
        master.mav.mission_request_list_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
