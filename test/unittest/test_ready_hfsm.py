# === PFAD-B FULL FILE: QGCR/test/unittest/test_ready_hfsm.py ===

import unittest
from unittest.mock import MagicMock, patch

from pymavlink import mavutil

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.main_state import MainState


class TestReadyHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.model.takeoff = MagicMock()
        self.fsm = ReadyHFSM(self.model)

    def test_enter_sets_state(self):
        state = self.fsm.on_update()

        self.assertEqual(state, MainState.READY)
        self.assertEqual(self.model.hfsm_main, "READY")
        self.assertEqual(self.model.hfsm_sub, "IDLE")

    def test_takeoff_before_first_tick_is_kept(self):
        self.model.hfsm_events.append("TAKEOFF")
        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)

    def test_stays_ready_and_ticks_takeoff(self):
        self.fsm.on_update()
        state = self.fsm.on_update()

        self.assertEqual(state, MainState.READY)
        self.assertEqual(self.model.takeoff.tick.call_count, 2)

    def test_takeoff_event_goes_airborne(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("TAKEOFF")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)

    def test_mission_tab_goes_mission(self):
        self.fsm.on_update()
        self.model.active_tab = "Mission"

        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

    def test_mission_tab_selected_during_enter_is_not_lost(self):
        """Tab-Klick vor dem ersten Tick (Enter leert hfsm_events) geht nicht verloren."""
        self.model.active_tab = "Mission"
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

    def test_log_tab_stays_ready(self):
        self.fsm.on_update()
        self.model.active_tab = "Log"

        self.assertEqual(self.fsm.on_update(), MainState.READY)

    def test_reset_event_goes_reset(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_connection_lost_ignored_during_grace_phase(self):
        self.fsm.on_update()
        self.model.px4_connected = False

        self.assertEqual(self.fsm.on_update(), MainState.READY)

    def test_connection_lost_after_grace_phase_goes_reset(self):
        with patch("QGCR.states.ready.ready_hfsm.time.time", return_value=1000.0):
            self.fsm.on_update()

        self.model.px4_connected = False

        with patch("QGCR.states.ready.ready_hfsm.time.time", return_value=1006.0):
            self.assertEqual(self.fsm.on_update(), MainState.RESET)

    # ------------------------------------------------------------
    # ARM / DISARM
    # ------------------------------------------------------------
    def make_connection(self, target_system=1):
        conn = MagicMock()
        conn.master.target_system = target_system
        conn.master.target_component = 1
        self.model.connection = conn
        return conn

    def sent_message(self, conn):
        conn.send.assert_called_once()
        return conn.send.call_args[0][0]

    def test_arm_sends_arm_command_and_stays_ready(self):
        conn = self.make_connection()
        self.fsm.on_update()
        self.model.hfsm_events.append("ARM")

        self.assertEqual(self.fsm.on_update(), MainState.READY)

        msg = self.sent_message(conn)
        self.assertEqual(msg.command, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)
        self.assertEqual(msg.param1, 1)
        self.assertEqual((msg.target_system, msg.target_component), (1, 1))
        self.assertIn("[QGCR] [ReadyHFSM] ARM gesendet", self.model.qgcr_logs())

    def test_disarm_sends_disarm_command(self):
        conn = self.make_connection()
        self.fsm.on_update()
        self.model.hfsm_events.append("DISARM")

        self.assertEqual(self.fsm.on_update(), MainState.READY)

        msg = self.sent_message(conn)
        self.assertEqual(msg.command, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)
        self.assertEqual(msg.param1, 0)

    def test_arm_without_px4_target_is_ignored(self):
        conn = self.make_connection(target_system=0)
        self.fsm.on_update()
        self.model.hfsm_events.append("ARM")

        self.assertEqual(self.fsm.on_update(), MainState.READY)
        conn.send.assert_not_called()
        self.assertIn("[QGCR] [ReadyHFSM] ARM ignoriert: noch kein PX4-Ziel", self.model.qgcr_logs())

    def test_arm_without_connection_is_ignored(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("ARM")

        self.assertEqual(self.fsm.on_update(), MainState.READY)


if __name__ == "__main__":
    unittest.main()
