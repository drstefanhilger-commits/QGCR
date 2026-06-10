import unittest
from types import SimpleNamespace
from pymavlink.dialects.v20 import common as mavlink
from QGCR.communication.event_router import EventRouter


class FakeFSM:
    def __init__(self, name: str):
        self.name = name
        self.messages = []

    def on_message(self, msg):
        self.messages.append(msg)


class FakeDispatcher:
    def __init__(self):
        self.startup_sm = FakeFSM("startup")
        self.ready_sm = FakeFSM("ready")
        self.takeoff_sm = FakeFSM("takeoff")
        self.mission_sm = FakeFSM("mission")
        self._active = self.ready_sm

    def get_active_fsm(self):
        return self._active

    def set_active(self, fsm_name: str):
        mapping = {
            "startup": self.startup_sm,
            "ready": self.ready_sm,
            "takeoff": self.takeoff_sm,
            "mission": self.mission_sm,
        }
        self._active = mapping[fsm_name]


class FakeHeartbeatMonitor:
    def __init__(self):
        self.calls = []

    def handle_heartbeat(self, msg, source: str):
        self.calls.append((source, msg))


def make_msg(msgid, **fields):
    ns = SimpleNamespace(**fields)
    ns._msgid = msgid
    ns.get_msgId = lambda: msgid
    return ns


class TestEventRouter(unittest.TestCase):

    def test_event_router_routing(self):
        dispatcher = FakeDispatcher()
        hb_monitor = FakeHeartbeatMonitor()
        router = EventRouter(dispatcher, hb_monitor)

        # 1) PARAM_VALUE → StartupFSM
        param_msg = make_msg(mavlink.MAVLINK_MSG_ID_PARAM_VALUE, param_id="TEST_PARAM")
        router.route(param_msg)
        self.assertEqual(dispatcher.startup_sm.messages, [param_msg])
        self.assertEqual(dispatcher.ready_sm.messages, [])
        self.assertEqual(dispatcher.mission_sm.messages, [])
        self.assertEqual(dispatcher.takeoff_sm.messages, [])

        # 2) HOME_POSITION → StartupFSM
        home_msg = make_msg(mavlink.MAVLINK_MSG_ID_HOME_POSITION, latitude=0, longitude=0)
        router.route(home_msg)
        self.assertEqual(dispatcher.startup_sm.messages[-1], home_msg)

        # 3) MISSION_REQUEST → MissionFSM
        mission_req = make_msg(mavlink.MAVLINK_MSG_ID_MISSION_REQUEST, seq=5)
        router.route(mission_req)
        self.assertEqual(dispatcher.mission_sm.messages, [mission_req])

        # 4) COMMAND_ACK → TakeoffFSM
        cmd_ack = make_msg(mavlink.MAVLINK_MSG_ID_COMMAND_ACK, command=22)
        router.route(cmd_ack)
        self.assertEqual(dispatcher.takeoff_sm.messages, [cmd_ack])

        # 5) Default → aktive FSM (ready)
        other_msg = make_msg(999, foo="bar")
        router.route(other_msg)
        self.assertEqual(dispatcher.ready_sm.messages, [other_msg])

        # 6) PX4-Heartbeat
        px4_hb = make_msg(
            mavlink.MAVLINK_MSG_ID_HEARTBEAT,
            type=mavlink.MAV_TYPE_QUADROTOR,
        )
        router.route(px4_hb)
        self.assertEqual(hb_monitor.calls[-1][0], "px4")
        self.assertEqual(hb_monitor.calls[-1][1], px4_hb)

        # 7) QGC-Heartbeat
        gcs_hb = make_msg(
            mavlink.MAVLINK_MSG_ID_HEARTBEAT,
            type=mavlink.MAV_TYPE_GCS,
        )
        router.route(gcs_hb)
        self.assertEqual(hb_monitor.calls[-1][0], "gcs")
        self.assertEqual(hb_monitor.calls[-1][1], gcs_hb)


if __name__ == "__main__":
    unittest.main()
