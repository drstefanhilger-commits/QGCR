# === PFAD-B FULL FILE: test_connection_gcs_heartbeat.py ===

import unittest
from unittest.mock import MagicMock, patch
import time

from QGCR.model.model import Model
from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher


class TestConnectionGCSHeartbeat(unittest.TestCase):

    @patch("QGCR.communication.connection.mavutil.mavlink_connection")
    def test_gcs_heartbeat_worker_sends(self, mock_conn):
        """
        Verifiziert:
        - Connection erzeugt nur EINE MAVLink-Verbindung
        - GCS-Heartbeat-Worker sendet über diese Verbindung
        - heartbeat_send() wird mindestens einmal aufgerufen
        """

        # Fake MAVLink-Objekt
        fake_mav = MagicMock()
        fake_mav.mav.heartbeat_send = MagicMock()

        mock_conn.return_value = fake_mav

        model = Model()
        dispatcher = Dispatcher(model)

        # WICHTIG: Connection erwartet NUR dispatcher
        conn = Connection(dispatcher, wait_for_heartbeat=False)

        # Worker etwas Zeit geben
        time.sleep(1.2)

        # Erwartung: heartbeat_send wurde aufgerufen
        self.assertGreaterEqual(fake_mav.mav.heartbeat_send.call_count, 1)

        # Erwartung: nur eine MAVLink-Verbindung
        mock_conn.assert_called_once()

        conn.close()


if __name__ == "__main__":
    unittest.main()
