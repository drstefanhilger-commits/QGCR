# === PFAD-B FULL FILE: QGCR/test/test_harness_mission_download.py ===

import unittest
from types import SimpleNamespace

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.communication.microservices.mission_download_microservice import MissionDownloadMicroService


class FakeModel:
    def __init__(self):
        self.services = SimpleNamespace()


class FakeMav:
    def __init__(self, parent):
        self.parent = parent

    def mission_request_list_send(self, *args):
        self.parent.sent.append(("MISSION_REQUEST_LIST", None))

    def mission_request_int_send(self, *args):
        seq = args[2]
        self.parent.sent.append(("MISSION_REQUEST_INT", seq))


class FakeMaster:
    def __init__(self):
        self.sent = []
        self.mav = FakeMav(self)

    def recv_match(self, *args, **kwargs):
        return None


class FakeConnection(Connection):
    def connect(self):
        self.master = FakeMaster()
        self._worker = None
        self._gcs_hb_thread = None


def make_mission_count(count):
    msg = SimpleNamespace()
    msg.get_type = lambda: "MISSION_COUNT"
    msg.count = count
    return msg


def make_mission_item_int(seq, cmd=16, x=47.0, y=8.0, z=10.0):
    msg = SimpleNamespace()
    msg.get_type = lambda: "MISSION_ITEM_INT"
    msg.seq = seq
    msg.command = cmd
    msg.x = int(x * 1e7)
    msg.y = int(y * 1e7)
    msg.z = int(z * 1000)
    return msg


class FakeMissionDownloadFSM:
    def __init__(self, service):
        self.service = service

    def start(self):
        self.service.start()

    def tick(self):
        self.service.tick()


class TestHarnessMissionDownload(unittest.TestCase):

    def test_mission_download_end_to_end(self):
        model = FakeModel()
        dispatcher = Dispatcher(model)
        conn = FakeConnection(model, dispatcher)
        conn.connect()

        service = MissionDownloadMicroService(
            connection=conn,
            model=model,
            timeout=0.3,
        )
        model.services.mission_download = service

        fsm = FakeMissionDownloadFSM(service)
        fsm.start()

        # Tick 1: REQUEST_LIST
        fsm.tick()
        self.assertEqual(conn.master.sent[0], ("MISSION_REQUEST_LIST", None))

        # PX4 sends MISSION_COUNT = 3
        service.on_mission_count(make_mission_count(3))

        # Tick 2: WAIT_COUNT -> REQUEST_ITEM (state change only)
        fsm.tick()
        self.assertEqual(service._state, service.STATE_REQUEST_ITEM)

        # Tick 3: REQUEST_ITEM -> send MISSION_REQUEST_INT(0)
        fsm.tick()
        self.assertEqual(conn.master.sent[1], ("MISSION_REQUEST_INT", 0))

        # PX4 sends item 0
        service.on_mission_item_int(make_mission_item_int(0))

        # Tick 4: WAIT_ITEM -> REQUEST_ITEM(1)
        fsm.tick()
        self.assertEqual(service._state, service.STATE_REQUEST_ITEM)

        # Tick 5: REQUEST_ITEM -> send MISSION_REQUEST_INT(1)
        fsm.tick()
        self.assertEqual(conn.master.sent[2], ("MISSION_REQUEST_INT", 1))

        # PX4 sends item 1
        service.on_mission_item_int(make_mission_item_int(1))

        # Tick 6: WAIT_ITEM -> REQUEST_ITEM(2)
        fsm.tick()
        self.assertEqual(service._state, service.STATE_REQUEST_ITEM)

        # Tick 7: REQUEST_ITEM -> send MISSION_REQUEST_INT(2)
        fsm.tick()
        self.assertEqual(conn.master.sent[3], ("MISSION_REQUEST_INT", 2))

        # PX4 sends item 2
        service.on_mission_item_int(make_mission_item_int(2))

        # Tick 8: WAIT_ITEM -> DONE
        fsm.tick()
        self.assertTrue(service.done)
        self.assertIsNone(service.error)


if __name__ == "__main__":
    unittest.main()
