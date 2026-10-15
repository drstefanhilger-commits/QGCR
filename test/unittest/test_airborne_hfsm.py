# === PFAD-B FULL FILE: QGCR/test/unittest/test_airborne_hfsm.py ===

import unittest
import math
from unittest.mock import MagicMock

from pymavlink import mavutil

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM
from QGCR.states.main_state import MainState


class TestAirborneHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True

        self.takeoff = MagicMock()
        self.takeoff.STATE_IDLE = "IDLE"
        self.takeoff.state = "IDLE"
        self.model.takeoff = self.takeoff

        self.fsm = AirborneHFSM(self.model)

    def test_enter_sets_state_and_starts_takeoff(self):
        state = self.fsm.on_update()

        self.assertEqual(state, MainState.AIRBORNE)
        self.assertEqual(self.model.hfsm_main, "AIRBORNE")
        self.assertEqual(self.model.hfsm_sub, "FLIGHT")
        self.takeoff.start.assert_called_once()

    def test_enter_does_not_restart_running_takeoff(self):
        self.takeoff.state = "WAIT_CLIMB"
        self.fsm.on_update()

        self.takeoff.start.assert_not_called()

    def test_stays_airborne_and_ticks_takeoff(self):
        self.fsm.on_update()
        state = self.fsm.on_update()

        self.assertEqual(state, MainState.AIRBORNE)
        self.assertEqual(self.takeoff.tick.call_count, 2)

    def test_reset_event_goes_reset(self):
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_connection_lost_goes_reset(self):
        self.fsm.on_update()
        self.model.px4_connected = False

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    # --------------------------------------------------------
    # LAND
    # --------------------------------------------------------
    def make_connection(self, target_system=1):
        conn = MagicMock()
        conn.master.target_system = target_system
        conn.master.target_component = 1
        self.model.connection = conn
        return conn

    def start_flight(self):
        conn = self.make_connection()
        self.model.px4_armed = True
        self.fsm.on_update()                     # enter
        return conn

    def test_land_sends_nav_land(self):
        conn = self.start_flight()
        self.model.hfsm_events.append("LAND")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)

        msg = conn.send.call_args[0][0]
        self.assertEqual(msg.command, mavutil.mavlink.MAV_CMD_NAV_LAND)
        self.assertTrue(math.isnan(msg.param5) and math.isnan(msg.param6))
        self.assertEqual(self.model.hfsm_sub, "LAND")
        self.takeoff.reset.assert_called_once()   # laufende Takeoff-Sequenz stoppen

    def test_stays_airborne_while_landing(self):
        self.start_flight()
        self.model.hfsm_events.append("LAND")
        self.fsm.on_update()

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)

    def test_landed_and_disarmed_goes_ready(self):
        self.start_flight()
        self.model.hfsm_events.append("LAND")
        self.fsm.on_update()

        self.model.px4_armed = False             # PX4 disarmt nach dem Aufsetzen
        self.assertEqual(self.fsm.on_update(), MainState.READY)
        self.assertEqual(self.takeoff.reset.call_count, 2)
        self.assertIn("[QGCR] [AirborneHFSM] gelandet und disarmed → READY", self.model.qgcr_logs())

    def test_disarm_without_land_stays_airborne(self):
        self.start_flight()
        self.model.px4_armed = False
        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)

    def test_second_land_is_ignored(self):
        conn = self.start_flight()
        self.model.hfsm_events.append("LAND")
        self.fsm.on_update()
        self.model.hfsm_events.append("LAND")
        self.fsm.on_update()

        conn.send.assert_called_once()

    def test_land_without_px4_target_is_ignored(self):
        conn = self.make_connection(target_system=0)
        self.fsm.on_update()
        self.model.hfsm_events.append("LAND")
        self.fsm.on_update()

        conn.send.assert_not_called()
        self.assertEqual(self.model.hfsm_sub, "FLIGHT")

    # --------------------------------------------------------
    # RESET im Flug: erst landen, dann RESET
    # --------------------------------------------------------
    def test_reset_in_flight_lands_first(self):
        conn = self.start_flight()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)
        self.assertEqual(conn.send.call_args[0][0].command, mavutil.mavlink.MAV_CMD_NAV_LAND)
        self.assertEqual(self.model.hfsm_sub, "RESET_LAND")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)   # Landung läuft

        self.model.px4_armed = False                                 # gelandet, disarmed
        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_reset_while_landing_becomes_reset_landing(self):
        conn = self.start_flight()
        self.model.hfsm_events.append("LAND")
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)
        conn.send.assert_called_once()                               # kein zweites NAV_LAND
        self.assertEqual(self.model.hfsm_sub, "RESET_LAND")

        self.model.px4_armed = False
        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_second_reset_forces_immediate_reset(self):
        self.start_flight()
        self.model.hfsm_events.append("RESET")
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_reset_when_not_armed_is_immediate(self):
        self.make_connection()
        self.fsm.on_update()
        self.model.px4_armed = False
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_reset_without_px4_target_is_immediate(self):
        self.make_connection(target_system=0)
        self.model.px4_armed = True
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_reset_during_mission_lands_then_resets(self):
        conn = self.start_flight()
        self.load_mission()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()
        self.model.hfsm_events.append("RESET")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)
        self.assertEqual(conn.send.call_args[0][0].command, mavutil.mavlink.MAV_CMD_NAV_LAND)

        self.model.px4_armed = False
        self.assertEqual(self.fsm.on_update(), MainState.RESET)
        self.assertFalse(self.model.mission_running)

    # --------------------------------------------------------
    # MISSION (im Flug / nach Start vom Boden)
    # --------------------------------------------------------
    def load_mission(self):
        self.model.add_mission_item(0, 22, 47.0, 8.0, 20.0)
        self.model.mission.ready = True

    def test_mission_start_in_flight(self):
        conn = self.start_flight()
        self.load_mission()
        self.model.mission_track = [(1.0, 2.0)]          # alter Track
        self.model.hfsm_events.append("MISSION_START")

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)

        msg = conn.send.call_args[0][0]
        self.assertEqual(msg.command, mavutil.mavlink.MAV_CMD_MISSION_START)
        self.assertTrue(self.model.mission_running)
        self.assertEqual(self.model.mission_track, [])
        self.assertEqual(self.model.hfsm_sub, "MISSION")
        self.takeoff.reset.assert_called()

    def test_mission_start_without_mission_is_ignored(self):
        conn = self.start_flight()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        conn.send.assert_not_called()
        self.assertFalse(self.model.mission_running)

    def test_mission_end_with_landing_goes_ready(self):
        self.start_flight()
        self.load_mission()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        self.model.px4_armed = False             # Mission hat gelandet, PX4 disarmt
        self.assertEqual(self.fsm.on_update(), MainState.READY)
        self.assertFalse(self.model.mission_running)

    def test_enter_with_running_mission_skips_takeoff(self):
        self.model.mission_running = True        # Start vom Boden (MissionHFSM)
        self.model.px4_armed = True
        fsm = AirborneHFSM(self.model)

        self.assertEqual(fsm.on_update(), MainState.AIRBORNE)
        self.takeoff.start.assert_not_called()
        self.assertEqual(self.model.hfsm_sub, "MISSION")

        self.model.px4_armed = False
        self.assertEqual(fsm.on_update(), MainState.READY)

    def test_land_during_mission(self):
        conn = self.start_flight()
        self.load_mission()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()
        self.model.hfsm_events.append("LAND")
        self.fsm.on_update()

        self.assertEqual(conn.send.call_args[0][0].command, mavutil.mavlink.MAV_CMD_NAV_LAND)
        self.assertEqual(self.model.hfsm_sub, "LAND")


if __name__ == "__main__":
    unittest.main()
