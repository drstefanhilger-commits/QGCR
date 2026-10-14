#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/test/unittest/test_microservices_param_microservice.py ===

import unittest
from unittest.mock import MagicMock, patch

from QGCR.communication.microservices.param_microservice import ParamMicroService


def make_param(param_id, value, index, count):
    return MagicMock(param_id=param_id, param_value=value,
                     param_index=index, param_count=count)


class TestMicroservicesParamMicroservice(unittest.TestCase):

    def setUp(self):
        self.master = MagicMock()
        self.ms = ParamMicroService(self.master, 1, 1)

    def test_start_requests_param_list(self):
        self.ms.start()

        self.assertTrue(self.ms.started)
        self.master.mav.param_request_list_send.assert_called_once_with(1, 1)

    def test_param_sync(self):
        self.master.recv_match.side_effect = [
            make_param("SYS_MC_EST_GROUP", 1.0, 0, 2),
            None,
            make_param("SYS_AUTOSTART", 4003.0, 1, 2),
        ]

        self.ms.start()
        for _ in range(3):
            self.ms.tick()

        self.assertTrue(self.ms.done)
        self.assertIsNone(self.ms.error)
        self.assertEqual(self.ms.expected_count, 2)
        self.assertEqual(self.ms.params, {"SYS_MC_EST_GROUP": 1.0, "SYS_AUTOSTART": 4003.0})

    def test_tick_before_start_does_nothing(self):
        self.ms.tick()
        self.master.recv_match.assert_not_called()

    def test_timeout(self):
        self.master.recv_match.return_value = None

        with patch("QGCR.communication.microservices.param_microservice.time.time",
                   return_value=100.0):
            self.ms.start()

        with patch("QGCR.communication.microservices.param_microservice.time.time",
                   return_value=104.0):
            self.ms.tick()

        self.assertIsInstance(self.ms.error, TimeoutError)
        self.assertFalse(self.ms.done)


if __name__ == "__main__":
    unittest.main()
