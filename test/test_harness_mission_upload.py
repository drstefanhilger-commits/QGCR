# === PFAD-B FULL FILE: QGCR/test/test_harness_mission_upload.py ===

import unittest
from types import SimpleNamespace

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.communication.microservices.mission_upload_microservice import MissionUploadMicroService


class FakeMission:
    def __init__(self):
        self.items = []
        self.count = 0


class FakeModel:
    def __init__(self):
        self.services = SimpleNamespace()
        self.mission = FakeMission()


class FakeMav:
    def __init__(self, parent):
        self.parent = parent

    def mission_count_send(self, target_system, target_component, count):
        self.parent.sent.append(("MISSION_COUNT", count))

    def mission_item_int_send(self, *args):
        seq = args[2]
        self.parent.sent.append(("MISSION_ITEM_INT", seq))


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


def make_mission_request_int(seq):
    msg = SimpleNamespace()
    msg.get_type = lambda: "MISSION_REQUEST_INT"
    msg.seq = seq
    return msg


def make_mission_ack():
    msg = SimpleNamespace()
    msg.get_type = lambda: "MISSION_ACK"
    msg.type = 0
    return msg


class FakeMissionUploadFSM:
    def __init__(self, service):
        self.service = service

    def start(self):
        self.service.start()

    def tick(self):
        self.service.tick()


class TestHarnessMissionUpload(unittest.TestCase):

    def test_mission_upload_end_to_end(self):
        model = FakeModel()
        dispatcher = Dispatcher(model)
        conn = FakeConnection(model, dispatcher)
        conn.connect()

        model.mission.items = [
            (0, 16, 47.0, 8.0, 10.0),
            (1, 16, 47.1, 8.1, 12.0),
            (2, 16, 47.2, 8.2, 15.0),
        ]
        model.mission.count = 3

        service = MissionUploadMicroService(
            connection=conn,
            model=model,
            timeout=0.3,
        )
        model.services.mission_upload = service

        fsm = FakeMissionUploadFSM(service)
        fsm.start()

        # Tick 1: SEND_COUNT
        fsm.tick()
        self.assertEqual(conn.master.sent[0], ("MISSION_COUNT", 3))

        # PX4 requests item 0
        service.on_mission_request_int(make_mission_request_int(0))

        # Tick 2: WAIT_REQUEST -> SEND_ITEM (nur Zustandswechsel)
        fsm.tick()
        self.assertEqual(service._state, service.STATE_SEND_ITEM)

        # Tick 3: SEND_ITEM -> send item 0
        fsm.tick()
        self.assertEqual(conn.master.sent[1], ("MISSION_ITEM_INT", 0))

        # PX4 requests item 1
        service.on_mission_request_int(make_mission_request_int(1))

        # Tick 4: WAIT_REQUEST -> SEND_ITEM
        fsm.tick()
        self.assertEqual(service._state, service.STATE_SEND_ITEM)

        # Tick 5: SEND_ITEM -> send item 1
        fsm.tick()
        self.assertEqual(conn.master.sent[2], ("MISSION_ITEM_INT", 1))

        # PX4 requests item 2
        service.on_mission_request_int(make_mission_request_int(2))

        # Tick 6: WAIT_REQUEST -> SEND_ITEM
        fsm.tick()
        self.assertEqual(service._state, service.STATE_SEND_ITEM)

        # Tick 7: SEND_ITEM -> send item 2
        fsm.tick()
        self.assertEqual(conn.master.sent[3], ("MISSION_ITEM_INT", 2))

        # PX4 sends ACK
        service.on_mission_ack(make_mission_ack())

        # Tick 8: WAIT_ACK -> DONE
        fsm.tick()
        self.assertTrue(service.done)
        self.assertIsNone(service.error)


if __name__ == "__main__":
    unittest.main()
