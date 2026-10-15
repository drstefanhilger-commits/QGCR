# === PFAD-B FULL FILE: QGCR/test/unittest/test_controller_main_controller.py ===

import tempfile
import unittest
from unittest.mock import MagicMock, patch

from QGCR.controller.main_controller import MainController
from QGCR.states.main_state import MainState
from QGCR.states.main_state_map import MAIN_STATE_MAP
from QGCR.test.unittest.dummy_model import DummyModel


@patch("QGCR.states.startup.startup_hfsm.PX4SwarmStarter")
class TestControllerMainController(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = DummyModel()
        self.model.base_path = self.tmp.name      # Reset-Backup nicht ins cwd
        self.model.takeoff = MagicMock()
        self.model.takeoff.STATE_IDLE = "IDLE"
        self.model.takeoff.state = "IDLE"
        self.model.px4_connected = True
        self.model.px4_heartbeat_count = 1
        self.ctrl = MainController(self.model, MAIN_STATE_MAP)

    def test_takeoff_right_after_ready_is_not_lost(self, _starter):
        self.ctrl.on_update()                       # STARTUP → READY (Wechsel)
        self.assertEqual(self.model.hfsm_main, "READY")

        # GUI sieht READY und klickt TAKEOFF, bevor ReadyHFSM ihren ersten Tick hatte
        self.model.hfsm_events.append("TAKEOFF")
        self.ctrl.on_update()

        self.assertEqual(self.ctrl.active_state, MainState.AIRBORNE)

    def test_reset_in_ready_is_immediate(self, _starter):
        self.ctrl.on_update()                            # → READY
        self.model.hfsm_events.append("RESET")
        self.ctrl.on_update()                            # RESET läuft in einem Tick durch → STARTUP

        self.assertIn("[QGCR] HFSM-Wechsel: READY → RESET", self.model.qgcr_logs())

    def test_reset_in_airborne_goes_to_airborne_hfsm(self, _starter):
        conn = MagicMock()
        conn.master.target_system = 1
        conn.master.target_component = 1
        self.model.connection = conn

        self.ctrl.on_update()                            # → READY
        self.model.hfsm_events.append("TAKEOFF")
        self.ctrl.on_update()                            # → AIRBORNE
        self.ctrl.on_update()                            # AIRBORNE: enter
        self.model.px4_armed = True

        self.model.hfsm_events.append("RESET")
        self.ctrl.on_update()

        self.assertEqual(self.ctrl.active_state, MainState.AIRBORNE)
        self.assertEqual(self.model.hfsm_sub, "RESET_LAND")

        self.model.px4_armed = False                     # gelandet
        self.ctrl.on_update()
        self.assertEqual(self.ctrl.active_state, MainState.RESET)

    def test_reset_behind_unread_event_in_startup(self, _starter):
        self.model.px4_connected = False                 # bleibt in STARTUP
        self.ctrl.on_update()
        self.model.hfsm_events.extend(["ARM", "RESET"])  # STARTUP liest ARM nie

        self.ctrl.on_update()

        self.assertIn("[QGCR] HFSM-Wechsel: STARTUP → RESET", self.model.qgcr_logs())
        self.assertNotIn("RESET", self.model.hfsm_events)

    def test_takeoff_done_in_airborne_keeps_hfsm(self, _starter):
        self.ctrl.on_update()                            # → READY
        self.model.hfsm_events.append("TAKEOFF")
        self.ctrl.on_update()                            # → AIRBORNE
        hfsm = self.ctrl.active_fsm

        self.model.hfsm_events.append("TAKEOFF_DONE")
        self.ctrl.on_update()

        self.assertIs(self.ctrl.active_fsm, hfsm)        # nicht neu erzeugt
        self.assertNotIn("TAKEOFF_DONE", self.model.hfsm_events)

    def test_stale_events_dropped_on_switch_to_ready(self, _starter):
        self.model.hfsm_events.append("TAKEOFF_ALT")     # Rest aus dem Vorzyklus
        self.ctrl.on_update()                            # STARTUP → READY

        self.assertEqual(self.ctrl.active_state, MainState.READY)
        self.assertEqual(len(self.model.hfsm_events), 0)


if __name__ == "__main__":
    unittest.main()
