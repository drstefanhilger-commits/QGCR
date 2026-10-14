# === PFAD-B FULL FILE: QGCR/test/unittest/test_connection_heartbeat_pipeline.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.fake_mavlink import make_msg, run_connection


def px4_heartbeat(armed=False, main_mode=4, sub_mode=3, system_status=3):
    return make_msg(
        "HEARTBEAT",
        base_mode=128 if armed else 0,
        custom_mode=(main_mode << 16) | (sub_mode << 24),
        system_status=system_status,
    )


class TestConnectionHeartbeatPipeline(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.dispatcher = MagicMock()

    def test_px4_heartbeat_reaches_model(self):
        run_connection(self.model, self.dispatcher, [px4_heartbeat()])

        self.assertTrue(self.model.px4_connected)
        self.assertEqual(self.model.px4_heartbeat_count, 1)
        self.assertEqual(self.model.px4_mode, "AUTO.LOITER")
        self.assertFalse(self.model.px4_armed)
        self.assertTrue(self.model.ready_to_arm)

    def test_heartbeat_is_not_dispatched(self):
        run_connection(self.model, self.dispatcher, [px4_heartbeat()])
        self.dispatcher.dispatch.assert_not_called()

    def test_armed_flag_and_not_ready_to_arm(self):
        run_connection(self.model, self.dispatcher,
                       [px4_heartbeat(armed=True, system_status=4)])

        self.assertTrue(self.model.px4_armed)
        self.assertFalse(self.model.ready_to_arm)

    def test_heartbeat_counter(self):
        run_connection(self.model, self.dispatcher, [px4_heartbeat()] * 3)
        self.assertEqual(self.model.px4_heartbeat_count, 3)


if __name__ == "__main__":
    unittest.main()
