# === PFAD-B FULL FILE: tests/test_ready_hfsm.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.ready_substate import ReadySubState
from QGCR.states.main_state import MainState


# ------------------------------------------------------------
# Hilfs-Mock für Model
# ------------------------------------------------------------
class MockModel:
    def __init__(self):
        self.queue_gui = MagicMock()
        self.update_status = MagicMock()

        # SubFSM-relevante Flags
        self.takeoff_requested = False
        self.px4_heartbeat_ok = True

        # MicroServices
        class Services:
            pass

        self.services = Services()
        self.services.takeoff = MagicMock()


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
# Test ReadyHFSM
# ------------------------------------------------------------
class TestReadyHFSM(unittest.TestCase):

    def setUp(self):
        self.model = MockModel()

        # Wir ersetzen die echten SubFSMs durch MockSubFSMs
        self.state_map = {
            ReadySubState.READY_IDLE: lambda m: MockSubFSM(m, ReadySubState.READY_IDLE),
            ReadySubState.READY_TAKEOFF: lambda m: MockSubFSM(m, ReadySubState.READY_TAKEOFF),
            ReadySubState.READY_HEARTBEAT_LOST: lambda m: MockSubFSM(m, ReadySubState.READY_HEARTBEAT_LOST),
        }

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def test_enter_calls_gui_and_status(self):
        fsm = ReadyHFSM(self.model, self.state_map)
        fsm._on_enter()

        self.model.update_status.assert_called_once()
        self.model.queue_gui.put.assert_called()

    # ------------------------------------------------------------
    # DURING: Idle bleibt Idle
    # ------------------------------------------------------------
    def test_idle_stays_idle(self):
        fsm = ReadyHFSM(self.model, self.state_map)
        fsm._on_enter()

        fsm._on_during()

        self.assertEqual(fsm.active_substate, ReadySubState.READY_IDLE)

    # ------------------------------------------------------------
    # DURING: Idle → Takeoff
    # ------------------------------------------------------------
    def test_idle_to_takeoff(self):
        fsm = ReadyHFSM(self.model, self.state_map)
        fsm._on_enter()

        # SubFSM soll TAKEOFF zurückgeben
        fsm.active_fsm.return_state = ReadySubState.READY_TAKEOFF

        fsm._on_during()

        self.assertEqual(fsm.active_substate, ReadySubState.READY_TAKEOFF)

    # ------------------------------------------------------------
    # DURING: Idle → Heartbeat Lost
    # ------------------------------------------------------------
    def test_idle_to_heartbeat_lost(self):
        fsm = ReadyHFSM(self.model, self.state_map)
        fsm._on_enter()

        fsm.active_fsm.return_state = ReadySubState.READY_HEARTBEAT_LOST

        fsm._on_during()

        self.assertEqual(fsm.active_substate, ReadySubState.READY_HEARTBEAT_LOST)

    # ------------------------------------------------------------
    # Events werden korrekt weitergeleitet
    # ------------------------------------------------------------
    def test_event_forwarding(self):
        fsm = ReadyHFSM(self.model, self.state_map)
        fsm._on_enter()

        fsm.active_fsm.handle_event_called = False
        fsm.handle_event("TEST_EVENT")

        self.assertTrue(fsm.active_fsm.handle_event_called)

    # ------------------------------------------------------------
    # Ungültiger Substate wird ignoriert
    # ------------------------------------------------------------
    def test_invalid_substate_is_ignored(self):
        fsm = ReadyHFSM(self.model, self.state_map)
        fsm._on_enter()

        # Simuliere ungültigen Rückgabewert
        fsm.active_fsm.return_state = "INVALID_STATE"

        fsm._on_during()

        # Substate bleibt unverändert
        self.assertEqual(fsm.active_substate, ReadySubState.READY_IDLE)


if __name__ == "__main__":
    unittest.main()
