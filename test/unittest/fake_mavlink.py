# === PFAD-B FULL FILE: QGCR/test/unittest/fake_mavlink.py ===

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

    return conn, master, mav_conn
