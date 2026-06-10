# === PFAD-B FULL FILE: QGCR/test/test_integration_ready_takeoff_airborne.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.states.main.main_hfsm import MainHFSM
from QGCR.states.main.main_state import MainState


# ------------------------------------------------------------
# Mock Model
# ------------------------------------------------------------
class MockModel:
    def __init__(self):
        # GUI
        self.update_status = MagicMock()

        # PX4
        self.px4_heartbeat_ok = True

        # Mission flags
        self.mission_requested = False

        # MicroServices
        class Services:
            pass

        self.services = Services()

        # Takeoff MicroService
        self.services.takeoff = MagicMock()
        self.services.takeoff.start = MagicMock()
        self.services.takeoff.tick = MagicMock()
        self.services.takeoff.done = False
        self.services.takeoff.error = None

        # Mission MicroService (Airborne)
        self.services.mission = MagicMock()
        self.services.mission.start = MagicMock()
        self.services.mission.tick = MagicMock()
        self.services.mission.done = False
        self.services.mission.error = None


# ------------------------------------------------------------
# Integration Test: READY → TAKEOFF → AIRBORNE
# ------------------------------------------------------------
class TestIntegrationReadyTakeoffAirborne(unittest.TestCase):

    def setUp(self):
        self.model = MockModel()
        self.hfsm = MainHFSM(self.model)

        # Initial tick to enter READY
        self.hfsm.on_update()

    # --------------------------------------------------------
    # 1) Initialzustand READY
    # --------------------------------------------------------
    def test_initial_state_is_ready(self):
        self.assertEqual(self.hfsm.state_enum, MainState.READY)

    # --------------------------------------------------------
    # 2) READY → TAKEOFF
    # --------------------------------------------------------
    def test_ready_to_takeoff(self):
        # TAKEOFF Event
        self.hfsm.handle_event("TAKEOFF")

        # Tick READY HFSM
        self.hfsm.on_update()

        # TakeoffMicroService muss gestartet werden
        self.model.services.takeoff.start.assert_called_once()

        # System bleibt noch in READY
        self.assertEqual(self.hfsm.state_enum, MainState.READY)

    # --------------------------------------------------------
    # 3) TAKEOFF → AIRBORNE
    # --------------------------------------------------------
    def test_takeoff_to_airborne(self):
        # TAKEOFF Event
        self.hfsm.handle_event("TAKEOFF")
        self.hfsm.on_update()

        # MicroService meldet Erfolg
        self.model.services.takeoff.done = True

        # Tick READY HFSM erneut
        self.hfsm.on_update()

        # Tick READY HFSM erneut
        self.hfsm.on_update()

        # Jetzt muss MainHFSM AIRBORNE sein
        self.assertEqual(self.hfsm.state_enum, MainState.AIRBORNE)

        # AirborneHFSM muss in HOLD starten
        airborne_hfsm = self.hfsm.active_hfsm
        self.assertEqual(
            airborne_hfsm.controller.active_substate.name,
            "AIRBORNE_HOLD"
        )


if __name__ == "__main__":
    unittest.main()
