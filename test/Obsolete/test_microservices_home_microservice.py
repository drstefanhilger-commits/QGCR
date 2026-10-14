#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock
from QGCR.communication.microservices.home_microservice import HomeMicroService


class TestMicroservicesHomeMicroservice(unittest.TestCase):

    def test_home_load(self):
        master = MagicMock()
        master.recv_match = MagicMock()

        msg = MagicMock(latitude=473977420, longitude=85455940, altitude=500)
        master.recv_match.return_value = msg

        ms = HomeMicroService(master, 1, 1)
        home = ms.load_home()

        self.assertEqual(home.latitude, 473977420)
        self.assertEqual(home.longitude, 85455940)
        self.assertEqual(home.altitude, 500)

        master.mav.command_long_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
