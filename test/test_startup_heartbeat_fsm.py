import unittest
from queue import Queue
from QGCR.states.startup.subfsms.startup_heartbeat_fsm import StartupHeartbeatFSM
from QGCR.states.startup_substate import SubState
from QGCR.events.event import Event, EventType
from QGCR.test.dummy_model import DummyModel


class TestStartupHeartbeatFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = StartupHeartbeatFSM(self.model)

    def test_initial_state(self):
        self.assertEqual(self.fsm.state_enum, SubState.STARTUP_HEARTBEAT)

    def test_no_heartbeat(self):
        next_state = self.fsm.on_update()
        self.assertEqual(next_state, SubState.STARTUP_HEARTBEAT)

    def test_heartbeat_event(self):
        # Heartbeat in Queue legen
        self.model.event_queue.put(Event(EventType.PX4_HEARTBEAT, {}))

        next_state = self.fsm.on_update()
        self.assertEqual(next_state, SubState.STARTUP_PARAMS)

    def test_handle_event(self):
        event = Event(EventType.PX4_HEARTBEAT, {})
        self.fsm.handle_event(event)
        self.assertTrue(self.model.px4_heartbeat_ok)


if __name__ == "__main__":
    unittest.main()
