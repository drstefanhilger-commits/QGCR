# === PFAD-B FULL FILE: test_connection_model_heartbeat.py ===

import unittest
from unittest.mock import MagicMock, patch
import time

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.model.model import Model


class HeartbeatMonitor:
    def __init__(self):
        self.received = []

    def on_message(self, msg_type, msg):
        self.received.append((msg_type, msg))


class TestConnectionModelHeartbeat(unittest.TestCase):

    @patch("QGCR.communication.connection.mavutil")
    def test_model_updates_on_heartbeat(self, mock_mavutil):
        """
        Verifiziert:
        - Connection empfängt HEARTBEAT
        - Dispatcher leitet HEARTBEAT an Monitor weiter
        """

        model = Model()
        dispatcher = Dispatcher(model)

        fake_conn = MagicMock()
        mock_mavutil.mavlink_connection.return_value = fake_conn

        fake_msg = MagicMock()
        fake_msg.get_type.return_value = "HEARTBEAT"

        fake_conn.recv_match.side_effect = [fake_msg] + [None] * 1000

        monitor = HeartbeatMonitor()
        dispatcher.subscribe(monitor, "HEARTBEAT")

        conn = Connection(dispatcher, wait_for_heartbeat=False)

        time.sleep(0.05)

        self.assertEqual(monitor.received, [("HEARTBEAT", fake_msg)])

        conn.close()


if __name__ == "__main__":
    unittest.main()
