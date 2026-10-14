# === PFAD-B FULL FILE: tests/test_ready_subfsms.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.states.ready.subfsms.ready_idle_fsm import ReadyIdleFSM
from QGCR.states.ready.subfsms.ready_takeoff_fsm import ReadyTakeoffFSM
from QGCR.states.ready.subfsms.ready_heartbeat_lost_fsm import ReadyHeartbeatLostFSM
from QGCR.states.ready.ready_substate import ReadySubState


# ------------------------------------------------------------
# Hilfs-Mock für das Model
# ------------------------------------------------------------
class MockModel:
    def __init__(self):
        self.takeoff_requested = False
        self.px4_heartbeat_ok = True
        self.queue_gui = MagicMock()
        self.update_status = MagicMock()

        # MicroServices
        class Services:
            pass

        self.services = Services()
        self.services.takeoff = MagicMock()


# ------------------------------------------------------------
# READY_IDLE TESTS
# ------------------------------------------------------------
class TestReadyIdleFSM(unittest.TestCase):

    def test_idle_stays_idle(self):
        model = MockModel()
        fsm = ReadyIdleFSM(model)

        fsm._on_enter()
        fsm._on_during()

        self.assertEqual(fsm._next_state, ReadySubState.READY_IDLE)

    def test_idle_to_takeoff(self):
        model = MockModel()
        model.takeoff_requested = True

        fsm = ReadyIdleFSM(model)
        fsm._on_during()

        self.assertEqual(fsm._next_state, ReadySubState.READY_TAKEOFF)

    def test_idle_to_heartbeat_lost(self):
        model = MockModel()
        model.px4_heartbeat_ok = False

        fsm = ReadyIdleFSM(model)
        fsm._on_during()

        self.assertEqual(fsm._next_state, ReadySubState.READY_HEARTBEAT_LOST)


# ------------------------------------------------------------
# READY_TAKEOFF TESTS
# ------------------------------------------------------------
class TestReadyTakeoffFSM(unittest.TestCase):

    def test_takeoff_stays_in_progress(self):
        model = MockModel()
        model.services.takeoff.done = False
        model.services.takeoff.error = None

        fsm = ReadyTakeoffFSM(model)
        fsm._on_enter()
        fsm._on_during()

        self.assertEqual(fsm._next_state, ReadySubState.READY_TAKEOFF)
        model.services.takeoff.start.assert_called_once()
        model.services.takeoff.tick.assert_called_once()

    def test_takeoff_completes(self):
        model = MockModel()
        model.services.takeoff.done = True
        model.services.takeoff.error = None

        fsm = ReadyTakeoffFSM(model)
        fsm._on_enter()
        fsm._on_during()

        self.assertEqual(fsm._next_state, ReadySubState.READY_IDLE)

    def test_takeoff_error(self):
        model = MockModel()
        model.services.takeoff.done = False
        model.services.takeoff.error = "ARM_FAILED"

        fsm = ReadyTakeoffFSM(model)
        fsm._on_enter()
        fsm._on_during()

        self.assertEqual(fsm._next_state, ReadySubState.READY_IDLE)
        model.update_status.assert_called()


# ------------------------------------------------------------
# READY_HEARTBEAT_LOST TESTS
# ------------------------------------------------------------
class TestReadyHeartbeatLostFSM(unittest.TestCase):

    def test_heartbeat_lost_stable(self):
        model = MockModel()
        fsm = ReadyHeartbeatLostFSM(model)

        fsm._on_enter()
        fsm._on_during()

        self.assertEqual(fsm._next_state, ReadySubState.READY_HEARTBEAT_LOST)

    def test_heartbeat_lost_ignores_events(self):
        model = MockModel()
        fsm = ReadyHeartbeatLostFSM(model)

        result = fsm.handle_event("ANY_EVENT")
        self.assertEqual(result, ReadySubState.READY_HEARTBEAT_LOST)


if __name__ == "__main__":
    unittest.main()
