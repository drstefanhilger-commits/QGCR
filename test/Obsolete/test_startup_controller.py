# === PFAD-B FULL FILE: test_startup_controller.py ===

import unittest
from queue import Queue

from QGCR.states.startup.startup_controller import StartupController
from QGCR.states.startup.startup_substate import StartupSubState as SubState
from QGCR.states.startup.subfsms.startup_heartbeat_fsm import StartupHeartbeatFSM
from QGCR.states.startup.subfsms.startup_param_sync_fsm import StartupParamSyncFSM
from QGCR.states.startup.subfsms.startup_home_fsm import StartupHomeFSM
from QGCR.states.startup.subfsms.startup_ok_fsm import StartupOKFSM


class DummyModel:
    def __init__(self):
        self.event_queue = Queue()
        self.px4_heartbeat_ok = False
        self.startup_ok = False


class TestStartupController(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()

        # echte Startup-Pipeline
        self.state_map = {
            SubState.STARTUP_HEARTBEAT: StartupHeartbeatFSM,
            SubState.STARTUP_PARAMS: StartupParamSyncFSM,
            SubState.STARTUP_HOME: StartupHomeFSM,
            SubState.STARTUP_OK: StartupOKFSM,
        }

        self.ctrl = StartupController(
            self.model,
            self.state_map,
            initial_state=SubState.STARTUP_HEARTBEAT
        )

    def test_initial_state(self):
        self.assertEqual(self.ctrl.current_state, SubState.STARTUP_HEARTBEAT)

    def test_event_routing(self):
        # Heartbeat in Queue legen
        from QGCR.events.event import Event, EventType
        self.model.event_queue.put(Event(EventType.PX4_HEARTBEAT, {}))

        next_state = self.ctrl.step()
        self.assertEqual(next_state, SubState.STARTUP_PARAMS)

    def test_full_sequence(self):
        from QGCR.events.event import Event, EventType

        # HEARTBEAT → PARAMS
        self.model.event_queue.put(Event(EventType.PX4_HEARTBEAT, {}))
        self.ctrl.step()
        self.assertEqual(self.ctrl.current_state, SubState.STARTUP_PARAMS)

        # PARAMS → HOME
        self.model.event_queue.put(Event(EventType.PX4_PARAMS_SYNCED, {}))
        self.ctrl.step()
        self.assertEqual(self.ctrl.current_state, SubState.STARTUP_HOME)

        # HOME → OK
        self.model.event_queue.put(Event(EventType.PX4_HOME_SET, {}))
        self.ctrl.step()
        self.assertEqual(self.ctrl.current_state, SubState.STARTUP_OK)


if __name__ == "__main__":
    unittest.main()
