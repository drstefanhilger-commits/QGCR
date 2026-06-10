# === PFAD-B FULL FILE: tests/test_ready_controller.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.states.ready.ready_controller import ReadyController
from QGCR.states.ready_substate import ReadySubState


# ------------------------------------------------------------
# Hilfs-Mock für Model
# ------------------------------------------------------------
class MockModel:
    def __init__(self):
        self.queue_gui = MagicMock()
        self.update_status = MagicMock()


# ------------------------------------------------------------
# Hilfs-Mock für SubFSMs
# ------------------------------------------------------------
class MockSubFSM:
    """Simuliert eine SubFSM mit kontrollierbarem Rückgabeverhalten."""

    def __init__(self, model, return_state):
        self.model = model
        self.return_state = return_state
        self.on_update_called = False
        self.handle_event_called = False

    def on_update(self):
        self.on_update_called = True
        return self.return_state

    def handle_event(self, event):
        self.handle_event_called = True
        return self.return_state


# ------------------------------------------------------------
# Test ReadyController
# ------------------------------------------------------------
class TestReadyController(unittest.TestCase):

    def setUp(self):
        self.model = MockModel()

        # Wir simulieren alle READY-SubFSMs
        self.state_map = {
            ReadySubState.READY_IDLE: lambda m: MockSubFSM(m, ReadySubState.READY_IDLE),
            ReadySubState.READY_TAKEOFF: lambda m: MockSubFSM(m, ReadySubState.READY_TAKEOFF),
            ReadySubState.READY_HEARTBEAT_LOST: lambda m: MockSubFSM(m, ReadySubState.READY_HEARTBEAT_LOST),

            # Dieser Eintrag muss vom Controller herausgefiltert werden
            "INVALID_STATE": lambda m: MockSubFSM(m, "INVALID_STATE"),
        }

    # ------------------------------------------------------------
    # Initialisierung
    # ------------------------------------------------------------
    def test_initial_state_is_idle(self):
        controller = ReadyController(self.model, self.state_map)
        self.assertEqual(controller.active_substate, ReadySubState.READY_IDLE)

    def test_invalid_states_are_filtered(self):
        controller = ReadyController(self.model, self.state_map)
        self.assertNotIn("INVALID_STATE", controller.state_map)

    # ------------------------------------------------------------
    # DURING / step()
    # ------------------------------------------------------------
    def test_step_stays_idle(self):
        controller = ReadyController(self.model, self.state_map)
        controller.step()
        self.assertEqual(controller.active_substate, ReadySubState.READY_IDLE)

    def test_step_switches_to_takeoff(self):
        controller = ReadyController(self.model, self.state_map)

        # SubFSM soll TAKEOFF zurückgeben
        controller.active_fsm.return_state = ReadySubState.READY_TAKEOFF

        controller.step()
        self.assertEqual(controller.active_substate, ReadySubState.READY_TAKEOFF)

    def test_step_switches_to_heartbeat_lost(self):
        controller = ReadyController(self.model, self.state_map)

        controller.active_fsm.return_state = ReadySubState.READY_HEARTBEAT_LOST

        controller.step()
        self.assertEqual(controller.active_substate, ReadySubState.READY_HEARTBEAT_LOST)

    def test_step_ignores_invalid_substate(self):
        controller = ReadyController(self.model, self.state_map)

        controller.active_fsm.return_state = "INVALID_STATE"

        controller.step()
        self.assertEqual(controller.active_substate, ReadySubState.READY_IDLE)

    # ------------------------------------------------------------
    # Events
    # ------------------------------------------------------------
    def test_event_forwarding(self):
        controller = ReadyController(self.model, self.state_map)

        controller.active_fsm.handle_event_called = False
        controller.handle_event("TEST_EVENT")

        self.assertTrue(controller.active_fsm.handle_event_called)

    def test_event_switches_state(self):
        controller = ReadyController(self.model, self.state_map)

        controller.active_fsm.return_state = ReadySubState.READY_TAKEOFF
        controller.handle_event("TEST_EVENT")

        self.assertEqual(controller.active_substate, ReadySubState.READY_TAKEOFF)

    def test_event_ignores_invalid_substate(self):
        controller = ReadyController(self.model, self.state_map)

        controller.active_fsm.return_state = "INVALID_STATE"
        controller.handle_event("TEST_EVENT")

        self.assertEqual(controller.active_substate, ReadySubState.READY_IDLE)


if __name__ == "__main__":
    unittest.main()
