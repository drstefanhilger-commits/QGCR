# === PFAD-B FULL FILE: test/test_ready_to_airborne_integration.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.ready.ready_controller import ReadyController
from QGCR.states.ready_substate import ReadySubState
from QGCR.states.main_state import MainState

from QGCR.services.takeoff_microservice import TakeoffMicroService


# ------------------------------------------------------------
# Mock Model
# ------------------------------------------------------------
class MockModel:
    def __init__(self):
        # GUI + Status
        self.queue_gui = MagicMock()
        self.update_status = MagicMock()

        # State flags
        self.takeoff_requested = False
        self.px4_heartbeat_ok = True

        # Main state
        self.main_state = MainState.READY

        # MicroServices
        class Services:
            pass

        self.services = Services()
        self.services.takeoff = MagicMock(spec=TakeoffMicroService)

        # MicroService flags
        self.services.takeoff.started = False
        self.services.takeoff.done = False
        self.services.takeoff.error = None


# ------------------------------------------------------------
# Integration Test: READY → TAKEOFF → AIRBORNE
# ------------------------------------------------------------
class TestReadyToAirborneIntegration(unittest.TestCase):

    def setUp(self):
        self.model = MockModel()

        # READY State Map wird automatisch geladen
        self.ready_hfsm = ReadyHFSM(self.model)

        # Controller für SubFSMs
        self.controller = ReadyController(self.model, self.ready_hfsm.state_map)

    # ------------------------------------------------------------
    # 1) READY_IDLE → TAKEOFF_REQUEST
    # ------------------------------------------------------------
    def test_ready_to_takeoff(self):
        # Start in READY_IDLE
        self.assertEqual(self.controller.active_substate, ReadySubState.READY_IDLE)

        # Benutzer fordert Takeoff an
        self.model.takeoff_requested = True

        # Tick
        self.controller.step()

        # Muss in READY_TAKEOFF wechseln
        self.assertEqual(self.controller.active_substate, ReadySubState.READY_TAKEOFF)

    # ------------------------------------------------------------
    # 2) TAKEOFF MicroService wird gestartet
    # ------------------------------------------------------------
    def test_takeoff_microservice_starts(self):
        self.model.takeoff_requested = True
        self.controller.step()

        # ENTER READY_TAKEOFF
        self.ready_hfsm.active_substate = ReadySubState.READY_TAKEOFF
        self.ready_hfsm.active_fsm = self.ready_hfsm.state_map[ReadySubState.READY_TAKEOFF](self.model)

        self.ready_hfsm.active_fsm._on_enter()

        self.model.services.takeoff.start.assert_called_once()

    # ------------------------------------------------------------
    # 3) TAKEOFF läuft → nicht fertig
    # ------------------------------------------------------------
    def test_takeoff_in_progress(self):
        self.model.takeoff_requested = True
        self.controller.step()

        # ENTER READY_TAKEOFF
        self.ready_hfsm.active_substate = ReadySubState.READY_TAKEOFF
        self.ready_hfsm.active_fsm = self.ready_hfsm.state_map[ReadySubState.READY_TAKEOFF](self.model)

        self.ready_hfsm.active_fsm._on_enter()

        # MicroService noch nicht fertig
        self.model.services.takeoff.done = False
        self.model.services.takeoff.error = None

        self.ready_hfsm.active_fsm._on_during()

        # Muss in READY_TAKEOFF bleiben
        self.assertEqual(self.ready_hfsm.active_fsm._next_state, ReadySubState.READY_TAKEOFF)

    # ------------------------------------------------------------
    # 4) TAKEOFF abgeschlossen → READY_IDLE → MainState = AIRBORNE
    # ------------------------------------------------------------
    def test_takeoff_completes_and_airborne_triggered(self):
        # Schritt 1: READY → TAKEOFF
        self.model.takeoff_requested = True
        self.controller.step()

        # Schritt 2: ENTER READY_TAKEOFF
        self.ready_hfsm.active_substate = ReadySubState.READY_TAKEOFF
        self.ready_hfsm.active_fsm = self.ready_hfsm.state_map[ReadySubState.READY_TAKEOFF](self.model)
        self.ready_hfsm.active_fsm._on_enter()

        # Schritt 3: MicroService meldet Erfolg
        self.model.services.takeoff.done = True
        self.model.services.takeoff.error = None

        self.ready_hfsm.active_fsm._on_during()

        # READY muss zurück nach READY_IDLE
        self.assertEqual(self.ready_hfsm.active_fsm._next_state, ReadySubState.READY_IDLE)

        # System-FSM würde jetzt AIRBORNE setzen
        self.model.main_state = MainState.AIRBORNE

        self.assertEqual(self.model.main_state, MainState.AIRBORNE)


if __name__ == "__main__":
    unittest.main()
