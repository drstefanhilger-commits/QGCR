# === PFAD-B FULL FILE: QGCR/test/unittest/test_connection.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.fake_mavlink import make_msg, run_connection


class TestConnection(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.dispatcher = MagicMock()

    def test_binds_gcs_port(self):
        _, _, mav_conn = run_connection(self.model, self.dispatcher, [])

        mav_conn.assert_called_once_with(
            "udp:0.0.0.0:14550",
            source_system=255,
            source_component=0,
            autoreconnect=False,
        )

    def test_command_ack_goes_to_model_and_dispatcher(self):
        ack = make_msg("COMMAND_ACK", command=400, result=0)
        run_connection(self.model, self.dispatcher, [ack])

        self.dispatcher.dispatch.assert_called_once_with(ack)
        self.assertIn(("status", "ACK: 400 → 0"), self.model.gui_items())

    def test_statustext_goes_to_px4_log_and_dispatcher(self):
        txt = make_msg("STATUSTEXT", text="Ready for takeoff", severity=6)
        run_connection(self.model, self.dispatcher, [txt])

        self.dispatcher.dispatch.assert_called_once_with(txt)
        self.assertEqual(
            self.model.queue_registry.px4_log_queue.get_nowait(),
            "[PX4-1] [STATUSTEXT:6] Ready for takeoff",
        )

    def test_other_messages_go_to_dispatcher(self):
        cnt = make_msg("MISSION_COUNT", count=2)
        run_connection(self.model, self.dispatcher, [cnt])

        self.dispatcher.dispatch.assert_called_once_with(cnt)

    def test_send_and_close(self):
        conn, master, _ = run_connection(self.model, self.dispatcher, [])

        conn.send("MSG")
        master.mav.send.assert_called_once_with("MSG")
        master.close.assert_called()


if __name__ == "__main__":
    unittest.main()
