#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/test/unittest/test_microservices_mission_microservice.py ===

import queue
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pymavlink import mavutil

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.fake_mavlink import make_msg, UpdatePump
from QGCR.test.utils.mission_item_builder import make_waypoint


ACCEPTED = mavutil.mavlink.MAV_MISSION_ACCEPTED


class FakePX4:
    """
    Simulierter PX4-Missionsmanager hinter einem MAVLink-Master.
    Antworten auf gesendete Nachrichten landen in einer Queue, die nur über
    recv_match() (also vom RX-Thread der Connection) gelesen werden kann.
    """

    def __init__(self, stored_items=0):
        self.inbox = queue.Queue()
        self.uploaded = {}
        self.upload_count = None
        self.stored = [SimpleNamespace(seq=i) for i in range(stored_items)]
        self.recv_threads = set()
        self.target_system = 1
        self.target_component = 1

        self.mav = MagicMock()
        self.mav.mission_count_send.side_effect = self._on_count
        self.mav.mission_item_int_send.side_effect = self._on_item
        self.mav.mission_request_list_send.side_effect = self._on_request_list
        self.mav.mission_request_int_send.side_effect = self._on_request_int

    # PX4 → GCS
    def _reply(self, msg_type, **fields):
        self.inbox.put(make_msg(msg_type, **fields))

    def recv_match(self, *args, **kwargs):
        self.recv_threads.add(threading.current_thread().name)
        try:
            return self.inbox.get(timeout=kwargs.get("timeout") or 0.05)
        except queue.Empty:
            return None

    def close(self):
        pass

    # GCS → PX4
    def _on_count(self, tsys, tcomp, count):
        self.upload_count = count
        self._reply("MISSION_REQUEST_INT", seq=0)

    def _on_item(self, tsys, tcomp, seq, *rest):
        self.uploaded[seq] = rest
        if seq + 1 < self.upload_count:
            self._reply("MISSION_REQUEST_INT", seq=seq + 1)
        else:
            self._reply("MISSION_ACK", type=ACCEPTED)

    def _on_request_list(self, tsys, tcomp):
        self._reply("MISSION_COUNT", count=len(self.stored))

    def _on_request_int(self, tsys, tcomp, seq):
        self._reply("MISSION_ITEM_INT", seq=seq)


def waypoints(n):
    return [make_waypoint(i, 47.0 + i * 0.001, 8.0, 10 + i) for i in range(n)]


class TestMissionMicroServiceUnit(unittest.TestCase):
    """
    Service ohne Connection: Antworten werden direkt per on_message() eingespeist.
    """

    def setUp(self):
        self.master = MagicMock()
        self.ms = MissionMicroService(self.master, 1, 1, timeout=0.2)

    def feed(self, msg_type, **fields):
        self.ms.on_message(msg_type, make_msg(msg_type, **fields))

    @patch("builtins.print")
    def test_upload_sequence(self, _print):
        mission = waypoints(2)
        self.master.mav.mission_count_send.side_effect = \
            lambda *a: self.feed("MISSION_REQUEST_INT", seq=0)
        self.master.mav.mission_item_int_send.side_effect = \
            lambda t, c, seq, *r: (self.feed("MISSION_REQUEST_INT", seq=1) if seq == 0
                                   else self.feed("MISSION_ACK", type=ACCEPTED))

        self.assertTrue(self.ms.upload(mission))

        self.master.mav.mission_count_send.assert_called_with(1, 1, 2)
        self.assertEqual(self.master.mav.mission_item_int_send.call_count, 2)
        self.master.recv_match.assert_not_called()

    @patch("builtins.print")
    def test_upload_rejected(self, _print):
        self.master.mav.mission_count_send.side_effect = \
            lambda *a: self.feed("MISSION_ACK", type=mavutil.mavlink.MAV_MISSION_ERROR)

        self.assertFalse(self.ms.upload(waypoints(1)))

    @patch("builtins.print")
    def test_upload_timeout(self, _print):
        self.assertFalse(self.ms.upload(waypoints(1)))

    @patch("builtins.print")
    def test_upload_invalid_seq(self, _print):
        self.master.mav.mission_count_send.side_effect = \
            lambda *a: self.feed("MISSION_REQUEST_INT", seq=5)

        self.assertFalse(self.ms.upload(waypoints(1)))
        self.master.mav.mission_item_int_send.assert_not_called()

    @patch("builtins.print")
    def test_download_sequence(self, _print):
        self.master.mav.mission_request_list_send.side_effect = \
            lambda *a: self.feed("MISSION_COUNT", count=2)
        self.master.mav.mission_request_int_send.side_effect = \
            lambda t, c, seq: self.feed("MISSION_ITEM_INT", seq=seq)

        mission = self.ms.download()

        self.assertEqual([m.seq for m in mission], [0, 1])
        self.master.mav.mission_request_list_send.assert_called_once()
        self.master.mav.mission_ack_send.assert_called_once_with(1, 1, ACCEPTED)
        self.master.recv_match.assert_not_called()

    @patch("builtins.print")
    def test_download_skips_wrong_seq(self, _print):
        self.master.mav.mission_request_list_send.side_effect = \
            lambda *a: self.feed("MISSION_COUNT", count=1)

        def answer(t, c, seq):
            self.feed("MISSION_ITEM_INT", seq=7)      # Duplikat/alt
            self.feed("MISSION_ITEM_INT", seq=seq)

        self.master.mav.mission_request_int_send.side_effect = answer

        self.assertEqual([m.seq for m in self.ms.download()], [0])

    @patch("builtins.print")
    def test_download_timeout(self, _print):
        self.assertEqual(self.ms.download(), [])
        self.master.mav.mission_ack_send.assert_not_called()

    @patch("builtins.print")
    def test_stale_messages_are_discarded(self, _print):
        self.feed("MISSION_ACK", type=ACCEPTED)        # Rest eines alten Transfers
        self.assertFalse(self.ms.upload(waypoints(1)))  # → Timeout statt falschem ACK

    # --------------------------------------------------------
    # Abbruch
    # --------------------------------------------------------
    def cancel_after(self, delay):
        cancel = threading.Event()
        threading.Timer(delay, cancel.set).start()
        return cancel

    def assert_cancel_ack(self):
        self.master.mav.mission_ack_send.assert_called_with(
            1, 1, mavutil.mavlink.MAV_MISSION_OPERATION_CANCELLED)
        self.assertEqual(self.ms.last_error, MissionMicroService.CANCELLED)

    @patch("builtins.print")
    def test_upload_cancel(self, _print):
        self.ms.timeout = 5.0
        start = time.monotonic()

        self.assertFalse(self.ms.upload(waypoints(2), cancel=self.cancel_after(0.2)))

        self.assertLess(time.monotonic() - start, 1.0)     # nicht erst nach Timeout
        self.assert_cancel_ack()

    @patch("builtins.print")
    def test_download_cancel_during_items(self, _print):
        self.ms.timeout = 5.0
        self.master.mav.mission_request_list_send.side_effect = \
            lambda *a: self.feed("MISSION_COUNT", count=3)
        self.master.mav.mission_request_int_send.side_effect = \
            lambda t, c, seq: self.feed("MISSION_ITEM_INT", seq=seq) if seq == 0 else None

        mission = self.ms.download(cancel=self.cancel_after(0.2))

        self.assertEqual([m.seq for m in mission], [0])
        self.assert_cancel_ack()
        self.assertEqual(self.master.mav.mission_ack_send.call_count, 1)  # kein ACCEPTED

    @patch("builtins.print")
    def test_cancel_before_start(self, _print):
        cancel = threading.Event()
        cancel.set()

        self.assertEqual(self.ms.download(cancel=cancel), [])
        self.assert_cancel_ack()

    @patch("builtins.print")
    def test_unset_cancel_does_not_interfere(self, _print):
        self.master.mav.mission_request_list_send.side_effect = \
            lambda *a: self.feed("MISSION_COUNT", count=0)

        self.assertEqual(self.ms.download(cancel=threading.Event()), [])
        self.assertIsNone(self.ms.last_error)

    def test_non_mission_messages_are_ignored(self):
        self.ms.on_message("HEARTBEAT", make_msg("HEARTBEAT"))
        self.assertTrue(self.ms._rx.empty())


class TestMissionMicroServiceWithConnection(unittest.TestCase):
    """
    Echter RX-Thread der Connection liest, Dispatcher liefert an model.mission_ms.
    """

    def setUp(self):
        self.model = DummyModel()
        self.px4 = FakePX4(stored_items=3)

        with patch("QGCR.communication.connection.mavutil.mavlink_connection",
                   return_value=self.px4):
            self.conn = Connection(self.model, Dispatcher(self.model))
            self.conn.connect()

        self.model.mission_ms = MissionMicroService(self.px4, 1, 1, timeout=2.0)
        self.pump = UpdatePump(self.conn).start()

    def tearDown(self):
        self.pump.stop()
        self.conn.close()
        self.conn._rx_thread.join(2)

    @patch("builtins.print")
    def test_upload_via_rx_thread(self, _print):
        self.assertTrue(self.model.mission_ms.upload(waypoints(4)))
        self.assertEqual(sorted(self.px4.uploaded), [0, 1, 2, 3])

    @patch("builtins.print")
    def test_download_via_rx_thread(self, _print):
        mission = self.model.mission_ms.download()
        self.assertEqual([m.seq for m in mission], [0, 1, 2])

    @patch("builtins.print")
    def test_only_rx_thread_reads(self, _print):
        self.model.mission_ms.upload(waypoints(2))
        self.model.mission_ms.download()

        self.assertEqual(self.px4.recv_threads, {self.conn._rx_thread.name})

    @patch("builtins.print")
    def test_cancel_via_rx_thread(self, _print):
        """PX4 antwortet nicht auf Item-Anforderungen → Stop bricht ab, PX4 bekommt CANCELLED."""
        self.px4.mav.mission_request_int_send.side_effect = None
        cancel = threading.Event()
        threading.Timer(0.3, cancel.set).start()

        mission = self.model.mission_ms.download(cancel=cancel)

        self.assertEqual(mission, [])
        self.px4.mav.mission_ack_send.assert_called_with(
            1, 1, mavutil.mavlink.MAV_MISSION_OPERATION_CANCELLED)


if __name__ == "__main__":
    unittest.main()
