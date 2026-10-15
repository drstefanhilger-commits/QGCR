# === PFAD-B FULL FILE: QGCR/test/unittest/fake_mavlink.py ===

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from QGCR.communication.connection import Connection


def make_msg(msg_type, src_system=1, src_component=1, **fields):
    """
    Erzeugt ein Objekt mit der MAVLink-Message-API, die Connection/Model nutzen.
    """
    msg = SimpleNamespace(**fields)
    msg.get_type = lambda: msg_type
    msg.get_srcSystem = lambda: src_system
    msg.get_srcComponent = lambda: src_component
    return msg


def run_connection(model, dispatcher, msgs, timeout=2.0):
    """
    Startet eine echte Connection mit gemocktem MAVLink-Master,
    spielt msgs über recv_match() ein und stoppt danach den RX-Thread.
    Liefert (conn, master, mavlink_connection_mock).
    """
    master = MagicMock()
    master.target_system = 1
    pending = list(msgs)

    conn = None

    def recv_match(*args, **kwargs):
        if pending:
            return pending.pop(0)
        conn._stop = True
        return None

    master.recv_match.side_effect = recv_match

    with patch("QGCR.communication.connection.mavutil.mavlink_connection",
               return_value=master) as mav_conn:
        conn = Connection(model, dispatcher)
        conn.connect()
        conn._rx_thread.join(timeout)
        conn.close()

    # Rolle des Update-Threads: Empfangenes an Model + Dispatcher verteilen
    conn.process_pending()

    return conn, master, mav_conn


class UpdatePump:
    """
    Ersetzt in Tests ohne Application den Update-Thread:
    ruft connection.process_pending() zyklisch auf (Single-Writer).
    """

    def __init__(self, connection, interval=0.01):
        self.connection = connection
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _run(self):
        while not self._stop.wait(self.interval):
            self.connection.process_pending()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2.0)
