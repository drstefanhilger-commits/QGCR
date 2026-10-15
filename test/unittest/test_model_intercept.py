# === PFAD-B FULL FILE: QGCR/test/unittest/test_model_intercept.py ===

import math
import unittest

from pymavlink import mavutil

from QGCR.model.intercept import (
    CHASE, HEAD_ON, InterceptConfig, Trigger, build_mission, enu_to_latlon, latlon_to_enu,
    plan_intercept, pursuit, reposition_command, return_time,
)

M = mavutil.mavlink
ORIGIN = (47.397971, 8.546164)


class TestModelIntercept(unittest.TestCase):

    def setUp(self):
        self.cfg = InterceptConfig()
        self.trigger = Trigger("T1", 1000.0, -150, 100, 20, 5, 0, 0)     # 5 m/s nach Osten

    def test_trigger_moves_with_constant_velocity(self):
        self.assertEqual(self.trigger.position_at(1010.0), (-100, 100, 20))
        self.assertEqual(self.trigger.ground_speed, 5)

    def test_wait_point_is_foot_of_perpendicular(self):
        """Kürzester Weg vom Start zur Trigger-Bahn (Geradengleichung)."""
        plan = plan_intercept(self.trigger, 1000.0, self.cfg)
        self.assertTrue(plan.reachable)
        self.assertEqual(plan.wait, (0.0, 100.0, 20.0))
        self.assertEqual(plan.heading_deg, 90.0)             # Osten
        self.assertAlmostEqual(plan.along, 150.0)
        self.assertAlmostEqual(plan.t_trigger, 30.0)

    def test_foot_point_diagonal(self):
        trigger = Trigger("D", 0, -200, -100, 20, 4, 3, 0)  # nach Nordost
        plan = plan_intercept(trigger, 0, self.cfg)
        e, n, _ = plan.wait
        self.assertAlmostEqual(e * 4 + n * 3, 0.0)           # Lot: senkrecht zur Flugrichtung
        self.assertAlmostEqual((e + 200) * 3 - (n + 100) * 4, 0.0)   # auf der Bahn

    def test_chase_when_trigger_first(self):
        plan = plan_intercept(self.trigger, 1000.0, self.cfg)    # Trigger nach 30 s, FSL nach 37 s
        self.assertGreater(plan.t_fsl, plan.t_trigger)
        self.assertEqual(plan.mode, CHASE)
        self.assertGreater(plan.meet[0], plan.wait[0])           # Treffpunkt hinter dem Wartepunkt

    def test_head_on_when_fsl_first(self):
        far = Trigger("F", 1000.0, -400, 100, 20, 5, 0, 0)
        plan = plan_intercept(far, 1000.0, self.cfg)
        self.assertTrue(plan.reachable)
        self.assertEqual(plan.mode, HEAD_ON)
        self.assertLess(plan.meet[0], plan.wait[0])              # dem Trigger entgegen
        # Treffzeit: beide gleich weit gekommen
        trigger_at = far.position_at(1000.0 + plan.t_fsl + plan.t_meet)
        self.assertAlmostEqual(trigger_at[0], plan.meet[0], places=6)

    def test_pursuit_times(self):
        v_f = self.cfg.ground_speed
        head_on = pursuit(self.trigger, (0, 100, 20), 1000.0, self.cfg)     # Trigger 150 m vorher
        self.assertEqual(head_on.mode, HEAD_ON)
        self.assertAlmostEqual(head_on.t_meet, 150 / (5 + v_f))
        chase = pursuit(self.trigger, (0, 100, 20), 1040.0, self.cfg)       # Trigger 50 m vorbei
        self.assertEqual(chase.mode, CHASE)
        self.assertAlmostEqual(chase.t_meet, 50 / (v_f - 5))
        self.assertAlmostEqual(chase.meet[0], 50 + 5 * chase.t_meet)

    def test_chase_impossible_if_trigger_faster(self):
        p = pursuit(Trigger("S", 0, -150, 100, 20, 9, 0, 0), (0, 100, 20), 30.0, self.cfg)
        self.assertEqual(p.mode, CHASE)
        self.assertIsNone(p.t_meet)

    def test_return_time(self):
        cfg = self.cfg
        t = return_time((0, 100, 20), cfg)                   # RTL: erst auf 60 m steigen
        self.assertAlmostEqual(t, 40 / cfg.climb_rate + 100 / cfg.ground_speed + 60 / cfg.land_rate
                               + cfg.approach_time + cfg.return_margin)
        high = return_time((0, 0, 80), cfg)                  # über RTL-Höhe: kein Steigen
        self.assertAlmostEqual(high, 80 / cfg.land_rate + cfg.approach_time + cfg.return_margin)

    def test_not_enough_time(self):
        plan = plan_intercept(self.trigger, 1000.0, InterceptConfig(timeout=60))
        self.assertFalse(plan.reachable)
        self.assertIn("Zeit reicht nicht", plan.reason)

    def test_no_200m_limit(self):
        far = Trigger("T3", 1000.0, -900, 300, 20, 3, 0, 0)
        plan = plan_intercept(far, 1000.0, InterceptConfig(timeout=600))
        self.assertTrue(plan.reachable)
        self.assertGreater(math.hypot(plan.wait[0], plan.wait[1]), 200.0)

    def test_planning_later_uses_current_trigger_position(self):
        plan = plan_intercept(self.trigger, 1010.0, self.cfg)
        self.assertEqual(plan.trigger_now, (-100, 100, 20))

    def test_unreachable_fast_trigger(self):
        plan = plan_intercept(Trigger("T2", 0, -30, 100, 20, 30, 0, 0), 0, self.cfg)
        self.assertFalse(plan.reachable)
        self.assertIn("Nachfliegen unmöglich", plan.reason)
        self.assertEqual(len(plan.path), 2)                  # Bahn trotzdem anzeigbar

    def test_stationary_trigger(self):
        plan = plan_intercept(Trigger("T0", 0, 50, 50, 20, 0, 0, 0), 0, self.cfg)
        self.assertFalse(plan.reachable)
        self.assertIn("bewegt sich nicht", plan.reason)

    def test_wait_altitude_follows_trigger_but_not_below_minimum(self):
        low = plan_intercept(Trigger("L", 0, -150, 100, 2, 5, 0, 0), 0, self.cfg)
        self.assertEqual(low.wait[2], self.cfg.min_alt)

        climbing = plan_intercept(Trigger("C", 0, -150, 100, 20, 5, 0, 0.5), 0, self.cfg)
        self.assertAlmostEqual(climbing.wait[2], 20 + 0.1 * 150)

    def test_enu_to_latlon(self):
        lat, lon = enu_to_latlon(ORIGIN, 0, 111.32)
        self.assertAlmostEqual(lat - ORIGIN[0], 0.001, places=6)
        self.assertAlmostEqual(lon, ORIGIN[1])

    def test_latlon_roundtrip(self):
        lat, lon = enu_to_latlon(ORIGIN, -123.4, 56.7)
        e, n = latlon_to_enu(ORIGIN, lat, lon)
        self.assertAlmostEqual(e, -123.4, places=6)
        self.assertAlmostEqual(n, 56.7, places=6)

    def test_build_mission(self):
        plan = plan_intercept(self.trigger, 1000.0, self.cfg)
        items = build_mission(plan, ORIGIN, self.cfg)

        self.assertEqual([i.command for i in items], [
            M.MAV_CMD_NAV_TAKEOFF, M.MAV_CMD_DO_CHANGE_SPEED, M.MAV_CMD_NAV_WAYPOINT,
            M.MAV_CMD_NAV_LOITER_UNLIM, M.MAV_CMD_NAV_LAND])
        self.assertEqual([i.seq for i in items], list(range(5)))
        self.assertEqual(items[0].z, 10.0)                            # Aufstieg 10 m
        self.assertEqual((items[1].param1, items[1].param2), (1, self.cfg.speed))
        self.assertEqual(items[2].param2, 1.0)                        # Wartepunkt: Annahmeradius 1 m
        wait_lat, wait_lon = enu_to_latlon(ORIGIN, *plan.wait[:2])
        self.assertEqual((items[2].x, items[2].y), (int(wait_lat * 1e7), int(wait_lon * 1e7)))
        self.assertEqual((items[3].x, items[3].y), (items[2].x, items[2].y))   # dort warten
        self.assertEqual((items[4].x, items[4].y, items[4].z),
                         (int(ORIGIN[0] * 1e7), int(ORIGIN[1] * 1e7), 0.0))    # Landen am Start

    def test_reposition_command(self):
        msg = reposition_command(1, 1, 47.4, 8.5, 520.0, 8.0)
        self.assertEqual(msg.command, M.MAV_CMD_DO_REPOSITION)
        self.assertEqual(msg.frame, M.MAV_FRAME_GLOBAL)
        self.assertEqual((msg.x, msg.y, msg.z), (474000000, 85000000, 520.0))
        self.assertEqual(msg.param1, 8.0)
        self.assertEqual(msg.param2, M.MAV_DO_REPOSITION_FLAGS_CHANGE_MODE)


if __name__ == "__main__":
    unittest.main()
