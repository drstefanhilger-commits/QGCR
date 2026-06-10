#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock
from QGCR.communication.microservices.param_microservice import ParamMicroService


class TestMicroservicesParamMicroservice(unittest.TestCase):

    def test_param_sync(self):
        master = MagicMock()
        master.recv_match = MagicMock()

        msg0 = MagicMock(param_id="SYS_MC_EST_GROUP", param_value=1.0,
                         param_index=0, param_count=2)
        msg1 = MagicMock(param_id="SYS_AUTOSTART", param_value=4010.0,
                         param_index=1, param_count=2)

        master.recv_match.side_effect = [msg0, msg1]

        ms = ParamMicroService(master, 1, 1)
        params = ms.sync()

        self.assertEqual(len(params), 2)
        self.assertIn("SYS_MC_EST_GROUP", params)
        self.assertIn("SYS_AUTOSTART", params)

        master.mav.param_request_list_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()

