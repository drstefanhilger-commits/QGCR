# === PFAD-B FULL FILE: test_airborne_controller.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.airborne.airborne_controller import AirborneController
from QGCR.states.airborne.airborne_substate import AirborneSubState


# ------------------------------------------------------------
# Dummy FSMs für isolierte Tests
# ------------------------------------------------------------

class DummyFSM_Base:
    """Basisklasse für Dummy-FSMs."""
    def __init__(self, model):
        self.model = model
        self.events_received = []

    def handle_event(self, event):
        self.events_received.append(event)


class DummyFSM_Takeoff(DummyFSM_Base):
    def on_update(self):
        return AirborneSubState.AIRBORNE_TAKEOFF


class DummyFSM_Mission(DummyFSM_Base):
    def on_update(self):
        return AirborneSubState.AIRBORNE_MISSION


class DummyFSM_Exit(DummyFSM_Base):
    def on_update(self):
        return AirborneSubState.AIRBORNE_EXIT


class DummyFSM_Lost(DummyFSM_Base):
    def on_update(self):
        return AirborneSubState.AIRBORNE_LOST


# ------------------------------------------------------------
# Testklasse
# ------------------------------------------------------------

class TestAirborneController(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()

        # State Map für Tests
        self.state_map = {
            AirborneSubState.AIRBORNE_TAKEOFF: DummyFSM_Takeoff,
            AirborneSubState.AIRBORNE_MISSION: DummyFSM_Mission,
            AirborneSubState.AIRBORNE_EXIT: DummyFSM_Exit,
            AirborneSubState.AIRBORNE_LOST: DummyFSM_Lost,
        }

        self.controller = AirborneController(
            model=self.model,
            state_map=self.state_map,
            initial_state=AirborneSubState.AIRBORNE_TAKEOFF
        )

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------

    def test_initial_fsm_is_created(self):
        self.assertIsInstance(self.controller.active_fsm, DummyFSM_Takeoff)
        self.assertEqual(self.controller.active_state, AirborneSubState.AIRBORNE_TAKEOFF)

    def test_step_keeps_same_fsm_if_state_unchanged(self):
        state = self.controller.step()
        self.assertEqual(state, AirborneSubState.AIRBORNE_TAKEOFF)
        self.assertIsInstance(self.controller.active_fsm, DummyFSM_Takeoff)

    def test_step_switches_fsm_on_state_change(self):
        # Ersetze aktive FSM durch Mission-FSM, die EXIT zurückgibt
        self.controller.active_fsm = DummyFSM_Mission(self.model)

        # Simuliere Transition: Mission → Exit
        self.controller.active_fsm.on_update = lambda: AirborneSubState.AIRBORNE_EXIT

        state = self.controller.step()

        self.assertEqual(state, AirborneSubState.AIRBORNE_EXIT)
        self.assertIsInstance(self.controller.active_fsm, DummyFSM_Exit)

    def test_handle_event_is_forwarded(self):
        # Dummy-Event kompatibel zum Controller
        class DummyEvent:
            def __init__(self):
                self.name = "TEST_EVENT"
                self.type = None  # kein FAILSAFE, kein SYSTEM

        event = DummyEvent()

        self.controller.handle_event(event)
        self.controller.step()  # Event wird verarbeitet

        self.assertIn(event, self.controller.active_fsm.events_received)


if __name__ == "__main__":
    unittest.main()
