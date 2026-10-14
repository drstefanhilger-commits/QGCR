# === PFAD-B FULL FILE: QGCR/test/unittest/test_sim_px4_swarm_starter_stop.py ===

import unittest
from unittest.mock import MagicMock, patch

from QGCR.sim.px4_swarm_starter import PX4SwarmStarter


class TestSimPX4SwarmStarterStop(unittest.TestCase):

    @patch("builtins.print")
    @patch("QGCR.sim.px4_swarm_starter.subprocess.run")
    def test_gazebo_kill_uses_exact_names(self, run, _print):
        starter = PX4SwarmStarter([], model=MagicMock())
        starter.running = True

        starter.stop_all()

        pkills = [c.args[0] for c in run.call_args_list if c.args[0][0] == "pkill"]
        self.assertTrue(pkills)
        for cmd in pkills:
            self.assertEqual(cmd[:3], ["pkill", "-9", "-x"], cmd)


if __name__ == "__main__":
    unittest.main()
