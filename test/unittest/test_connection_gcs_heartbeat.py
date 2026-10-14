# === PFAD-B FULL FILE: QGCR/test/unittest/test_connection_gcs_heartbeat.py ===

import time
import unittest
from unittest.mock import MagicMock, patch

from QGCR.communication.connection import Connection
from QGCR.test.unittest.dummy_model import DummyModel


class TestConnectionGCSHeartbeat(unittest.TestCase):

    @patch("QGCR.communication.connection.mavutil.mavlink_connection")
    def test_gcs_heartbeat_worker_sends(self, mock_conn):
        """
        Verifiziert:
        - Connection erzeugt nur EINE MAVLink-Verbindung
        - GCS-Heartbeat-Worker sendet über diese Verbindung als MAV_TYPE_GCS
        """
        master = MagicMock()
        master.recv_match.return_value = None
        mock_conn.return_value = master

        conn = Connection(DummyModel(), MagicMock())
        conn.connect()

        deadline = time.time() + 2.0
        while master.mav.heartbeat_send.call_count == 0 and time.time() < deadline:
            time.sleep(0.05)

        conn.close()

        mock_conn.assert_called_once()
        self.assertGreaterEqual(master.mav.heartbeat_send.call_count, 1)

        args = master.mav.heartbeat_send.call_args[0]
        self.assertEqual(args[0], 6)   # MAV_TYPE_GCS
        self.assertEqual(args[1], 8)   # MAV_AUTOPILOT_INVALID


if __name__ == "__main__":
    unittest.main()
