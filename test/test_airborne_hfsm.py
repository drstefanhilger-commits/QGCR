# === PFAD-B FULL FILE: test/test_airborne_hfsm.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.states.airborne.airborne_hfsm import AirborneHFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState
from QGCR.states.main_state import MainState


# ------------------------------------------------------------
# Mock Model
# ------------------------------------------------------------
class MockModel:
    def __init__(self):
        # Status + GUI
        self.update_status = MagicMock()

        # PX4 Status
        self.px4_heartbeat_ok = True

        # Mission flags
        self.mission_requested = False

        # MicroServices
        class Services:
            pass

        self.services = Services()
        self.services.mission = MagicMock()
        self.services.mission.start = MagicMock()
        self.services.mission.tick = MagicMock()
        self.services.mission.done = False
        self.services.mission.error = None

        # Main state
        self.main_state = MainState.AIRBORNE


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------
class TestAirborneHFSM(unittest.TestCase):

    def setUp(self):
        self.model = MockModel()
        self.hfsm = AirborneHFSM(self.model)

    # --------------------------------------------------------
    # Initialisierung
    # --------------------------------------------------------
    def test_initial_state_is_hold(self):
        self.assertEqual(self.hfsm.controller.active_substate,
                         AirborneSubState.AIRBORNE_HOLD)

    # --------------------------------------------------------
    # HOLD → LOST
    # --------------------------------------------------------
    def test_hold_switches_to_lost(self):
        self.model.px4_heartbeat_ok = False

        self.hfsm._on_during()

        self.assertEqual(self.hfsm.controller.active_substate,
                         AirborneSubState.AIRBORNE_LOST)

    # --------------------------------------------------------
    # HOLD → MISSION
    # --------------------------------------------------------
    def test_hold_switches_to_mission(self):
        self.model.mission_requested = True

        self.hfsm._on_during()

        self.assertEqual(self.hfsm.controller.active_substate,
                         AirborneSubState.AIRBORNE_MISSION)

    # --------------------------------------------------------
    # MISSION: MicroService start
    # --------------------------------------------------------
    def test_mission_starts_microservice(self):
        self.model.mission_requested = True
        self.hfsm._on_during()  # switch to mission

        # ENTER mission
        self.hfsm.controller.active_fsm._on_enter()

        self.model.services.mission.start.assert_called_once()

    # --------------------------------------------------------
    # MISSION → LOST (Fehler)
    # --------------------------------------------------------
    def test_mission_error_switches_to_lost(self):
        self.model.mission_requested = True
        self.hfsm._on_during()  # switch to mission

        # Fehler simulieren
        self.model.services.mission.error = "FAIL"

        self.hfsm._on_during()

        self.assertEqual(self.hfsm.controller.active_substate,
                         AirborneSubState.AIRBORNE_LOST)

    # --------------------------------------------------------
    # MISSION → HOLD (Erfolg)
    # --------------------------------------------------------
    def test_mission_done_switches_to_hold(self):
        self.model.mission_requested = True
        self.hfsm._on_during()  # switch to mission

        # Erfolg simulieren
        self.model.services.mission.done = True

        self.hfsm._on_during()

        self.assertEqual(self.hfsm.controller.active_substate,
                         AirborneSubState.AIRBORNE_HOLD)

    # --------------------------------------------------------
    # LOST bleibt LOST
    # --------------------------------------------------------
    def test_lost_is_sticky(self):
        self.model.px4_heartbeat_ok = False
        self.hfsm._on_during()  # switch to LOST

        # heartbeat wieder ok → LOST bleibt LOST
        self.model.px4_heartbeat_ok = True
        self.hfsm._on_during()

        self.assertEqual(self.hfsm.controller.active_substate,
                         AirborneSubState.AIRBORNE_LOST)

    # --------------------------------------------------------
    # EXIT → MainState READY
    # --------------------------------------------------------
    def test_exit_switches_main_state(self):
        # Manuell in EXIT setzen
        self.hfsm.controller.active_substate = AirborneSubState.AIRBORNE_EXIT
        self.hfsm.controller.active_fsm = self.hfsm.controller.state_map[
            AirborneSubState.AIRBORNE_EXIT
        ](self.model)

        self.hfsm._on_during()
        next_state = self.hfsm._on_exit()

        self.assertEqual(next_state, MainState.READY)


if __name__ == "__main__":
    unittest.main()
