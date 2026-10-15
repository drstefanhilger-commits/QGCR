# === PFAD-B FULL FILE: QGCR/test/unittest/test_model_intercept.py ===

import dataclasses
import math
import unittest

from pymavlink import mavutil

from QGCR.model.intercept import (
    InterceptConfig, Trigger, build_mission, enu_to_latlon, fsl_time_to, plan_intercept,
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

    def test_wait_point_is_reachable_and_ahead(self):
        plan = plan_intercept(self.trigger, 1000.0, self.cfg)

        self.assertTrue(plan.reachable)
        e, n, u = plan.wait
        self.assertAlmostEqual(n, 100.0)                     # auf der Trigger-Bahn
        self.assertAlmostEqual(u, 20.0)
        self.assertEqual(plan.heading_deg, 90.0)             # Osten
        # rechtzeitig: FSL da, bevor der Trigger 10 m vor dem Punkt ist
        self.assertLessEqual(plan.t_fsl, (plan.along - 10.0) / 5.0)
        self.assertAlmostEqual(plan.hold, (plan.along - 10.0) / 5.0 - plan.t_fsl)

    def test_wait_point_is_the_earliest(self):
        plan = plan_intercept(self.trigger, 1000.0, self.cfg)
        s = plan.along - self.cfg.step
        p = (-150 + s, 100, 20)
        self.assertGreater(fsl_time_to(p, self.cfg), (s - 10.0) / 5.0)

    def test_no_200m_limit(self):
        far = Trigger("T3", 1000.0, -900, 400, 20, 6, 0, 0)
        plan = plan_intercept(far, 1000.0, self.cfg)
        self.assertTrue(plan.reachable)
        self.assertGreater(math.hypot(plan.wait[0], plan.wait[1]), 200.0)

    def test_planning_later_uses_current_trigger_position(self):
        plan = plan_intercept(self.trigger, 1010.0, self.cfg)
        self.assertEqual(plan.trigger_now, (-100, 100, 20))

    def test_unreachable_fast_trigger(self):
        plan = plan_intercept(Trigger("T2", 0, -30, 100, 20, 30, 0, 0), 0, self.cfg)
        self.assertFalse(plan.reachable)
        self.assertIn("kein Wartepunkt", plan.reason)
        self.assertEqual(len(plan.path), 2)                  # Bahn trotzdem anzeigbar

    def test_stationary_trigger(self):
        plan = plan_intercept(Trigger("T0", 0, 50, 50, 20, 0, 0, 0), 0, self.cfg)
        self.assertFalse(plan.reachable)
        self.assertIn("bewegt sich nicht", plan.reason)

    def test_wait_altitude_follows_trigger_but_not_below_minimum(self):
        low = plan_intercept(Trigger("L", 0, -150, 100, 2, 5, 0, 0), 0, self.cfg)
        self.assertEqual(low.wait[2], self.cfg.min_alt)

        climbing = plan_intercept(Trigger("C", 0, -150, 100, 20, 5, 0, 0.5), 0, self.cfg)
        self.assertAlmostEqual(climbing.wait[2], 20 + 0.1 * climbing.along)

    def test_follow_end_is_10s_towards_trigger(self):
        """Ab dem Wartepunkt fliegt die FSL dem Trigger entgegen (gegen seine Flugrichtung)."""
        plan = plan_intercept(self.trigger, 1000.0, self.cfg)          # Trigger fliegt nach Osten
        follow = self.cfg.speed * self.cfg.speed_efficiency * self.cfg.follow_time
        self.assertAlmostEqual(plan.follow_end[0] - plan.wait[0], -follow)   # nach Westen
        self.assertAlmostEqual(plan.follow_end[1], plan.wait[1])
        self.assertAlmostEqual(plan.follow_end[2], plan.wait[2])

    def test_follow_direction_diagonal(self):
        trigger = Trigger("D", 0, -200, -200, 20, 4, 3, 0)               # nach Nordost
        plan = plan_intercept(trigger, 0, self.cfg)
        de, dn = plan.follow_end[0] - plan.wait[0], plan.follow_end[1] - plan.wait[1]
        self.assertAlmostEqual(de / dn, 4 / 3)                           # auf der Bahn ...
        self.assertLess(de, 0)                                          # ... nach Südwest
        self.assertLess(dn, 0)
        tn = plan.trigger_now
        dist = lambda p: math.hypot(p[0] - tn[0], p[1] - tn[1])
        self.assertLess(dist(plan.follow_end), dist(plan.wait))          # näher am Trigger

    def test_enu_to_latlon(self):
        lat, lon = enu_to_latlon(ORIGIN, 0, 111.32)
        self.assertAlmostEqual(lat - ORIGIN[0], 0.001, places=6)
        self.assertAlmostEqual(lon, ORIGIN[1])

    def test_build_mission(self):
        # frühester Wartepunkt → Wartezeit ≈ 0; LOITER_TIME nur bei Wartezeit ≥ 1 s
        plan = dataclasses.replace(plan_intercept(self.trigger, 1000.0, self.cfg), hold=12.0)
        items = build_mission(plan, ORIGIN, self.cfg)

        self.assertEqual([i.command for i in items], [
            M.MAV_CMD_NAV_TAKEOFF, M.MAV_CMD_DO_CHANGE_SPEED, M.MAV_CMD_NAV_WAYPOINT,
            M.MAV_CMD_NAV_LOITER_TIME, M.MAV_CMD_NAV_WAYPOINT, M.MAV_CMD_NAV_LAND])
        self.assertEqual([i.seq for i in items], list(range(6)))
        self.assertEqual(items[0].z, 10.0)                            # Aufstieg 10 m
        self.assertEqual((items[1].param1, items[1].param2), (1, self.cfg.speed))
        self.assertEqual(items[2].param2, 1.0)                        # Wartepunkt: Annahmeradius 1 m
        self.assertAlmostEqual(items[3].param1, 12.0)
        wait_lat, wait_lon = enu_to_latlon(ORIGIN, *plan.wait[:2])
        self.assertEqual((items[2].x, items[2].y), (int(wait_lat * 1e7), int(wait_lon * 1e7)))
        self.assertEqual((items[5].x, items[5].y, items[5].z),
                         (int(ORIGIN[0] * 1e7), int(ORIGIN[1] * 1e7), 0.0))    # Landen am Start

    def test_build_mission_without_hold(self):
        plan = plan_intercept(self.trigger, 1000.0, self.cfg)        # hold ≈ 0
        commands = [i.command for i in build_mission(plan, ORIGIN, self.cfg)]
        self.assertNotIn(M.MAV_CMD_NAV_LOITER_TIME, commands)


if __name__ == "__main__":
    unittest.main()
