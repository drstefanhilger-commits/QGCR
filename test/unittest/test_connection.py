# === PFAD-B FULL FILE: QGCR/test/unittest/test_connection.py ===

import threading
import unittest
from unittest.mock import MagicMock, patch

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.communication.connection import Connection
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


class TestConnectionSingleWriter(unittest.TestCase):
    """
    RX-Thread liest nur; Model + Dispatcher werden erst in process_pending()
    (Update-Thread) bedient.
    """

    def setUp(self):
        self.model = DummyModel()
        self.dispatcher = MagicMock()
        self.msgs = [
            make_msg("HEARTBEAT", base_mode=0, custom_mode=4 << 16, system_status=3),
            make_msg("MISSION_COUNT", count=1),
        ]

    def connect_and_receive(self):
        master = MagicMock()
        master.target_system = 1
        pending = list(self.msgs)

        def recv_match(*a, **k):
            if pending:
                return pending.pop(0)
            conn._stop = True
            return None

        master.recv_match.side_effect = recv_match
        with patch("QGCR.communication.connection.mavutil.mavlink_connection", return_value=master):
            conn = Connection(self.model, self.dispatcher)
            conn.connect()
            conn._rx_thread.join(2.0)
        self.addCleanup(conn.close)
        return conn

    def test_rx_thread_does_not_touch_model(self):
        self.connect_and_receive()

        self.assertEqual(self.model.px4_heartbeat_count, 0)
        self.dispatcher.dispatch.assert_not_called()

    def test_process_pending_applies_in_calling_thread(self):
        conn = self.connect_and_receive()
        threads = []
        self.dispatcher.dispatch.side_effect = lambda msg: threads.append(threading.current_thread())

        self.assertEqual(conn.process_pending(), 2)

        self.assertEqual(self.model.px4_heartbeat_count, 1)
        self.assertEqual(threads, [threading.current_thread()])
        self.assertEqual(conn.process_pending(), 0)

    def test_clear_pending_drops_messages(self):
        conn = self.connect_and_receive()
        conn.clear_pending()

        self.assertEqual(conn.process_pending(), 0)
        self.assertEqual(self.model.px4_heartbeat_count, 0)

    def test_error_in_one_message_does_not_stop_others(self):
        self.msgs.insert(0, make_msg("COMMAND_ACK"))       # ohne command/result → Fehler im Model
        conn = self.connect_and_receive()

        with patch("builtins.print"):
            self.assertEqual(conn.process_pending(), 3)
        self.assertEqual(self.model.px4_heartbeat_count, 1)


if __name__ == "__main__":
    unittest.main()
