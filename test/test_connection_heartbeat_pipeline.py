# === PFAD-B FULL FILE: test_connection_heartbeat_pipeline.py ===

import unittest
from unittest.mock import MagicMock, patch
import time

from QGCR.model.model import Model
from QGCR.communication.connection import Connection


class DummyDispatcher:
    def __init__(self):
        self.subscriptions = {}

    def subscribe(self, fsm, msg_type):
        self.subscriptions.setdefault(msg_type, []).append(fsm)

    def route_message(self, msg_type, msg):
        for fsm in self.subscriptions.get(msg_type, []):
            if hasattr(fsm, "on_message"):
                fsm.on_message(msg_type, msg)


class HeartbeatMonitor:
    def __init__(self):
        self.received = []

    def on_message(self, msg_type, msg):
        self.received.append((msg_type, msg))


class TestConnectionHeartbeatPipeline(unittest.TestCase):

    @patch("QGCR.communication.connection.mavutil")
    def test_px4_heartbeat_reaches_monitor(self, mock_mavutil):

        fake_conn = MagicMock()
        mock_mavutil.mavlink_connection.return_value = fake_conn

        fake_msg = MagicMock()
        fake_msg.get_type.return_value = "HEARTBEAT"

        fake_conn.recv_match.side_effect = [fake_msg] + [None] * 1000

        dispatcher = DummyDispatcher()
        monitor = HeartbeatMonitor()
        dispatcher.subscribe(monitor, "HEARTBEAT")

        # WICHTIG: Connection erwartet NUR dispatcher
        conn = Connection(dispatcher, wait_for_heartbeat=False)

        time.sleep(0.05)

        self.assertEqual(monitor.received, [("HEARTBEAT", fake_msg)])

        conn.close()


if __name__ == "__main__":
    unittest.main()
