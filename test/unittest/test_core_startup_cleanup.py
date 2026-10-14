# === PFAD-B FULL FILE: QGCR/test/unittest/test_core_startup_cleanup.py ===

import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from QGCR.core.startup_cleanup import StartupCleanup


def pgrep(pattern):
    out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True).stdout
    return {int(p) for p in out.split()}


class TestCoreStartupCleanupPatterns(unittest.TestCase):
    """
    Prüft die pkill-Muster mit echtem pgrep gegen Lockvogel-Prozesse (es wird nichts gekillt).
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            p.kill()
            p.wait()
        self.tmp.cleanup()

    def spawn_argv0(self, argv0, *args):
        """sleep mit beliebigem argv[0] (bash exec -a)."""
        cmd = "exec -a " + argv0 + " sleep 30 " + " ".join(args)
        p = subprocess.Popen(["bash", "-c", cmd])
        self.procs.append(p)
        return p.pid

    def spawn_python(self, *args):
        p = subprocess.Popen([sys.executable, *args])
        self.procs.append(p)
        return p.pid

    def matched(self):
        time.sleep(0.3)   # exec abwarten
        pids = set()
        for pattern in StartupCleanup.kill_patterns():
            pids |= pgrep(pattern)
        return pids

    def test_matches_px4_binary_with_path(self):
        pid = self.spawn_argv0("/home/x/PX4-Autopilot/build/px4_sitl_default/bin/px4")
        self.assertIn(pid, self.matched())

    def test_matches_gz_sim(self):
        pid = self.spawn_argv0("gz")
        self.assertIn(pid, self.matched())

    def test_matches_python_script(self):
        script = os.path.join(self.tmp.name, "px4_swarm_starter.py")
        with open(script, "w") as f:
            f.write("import time\ntime.sleep(30)\n")

        p = subprocess.Popen(["python3", script])
        self.procs.append(p)

        self.assertIn(p.pid, self.matched())

    def test_does_not_match_innocent_processes(self):
        sleeper = "import time; time.sleep(30)"
        pids = {
            self.spawn_python("-c", sleeper, "test_px4_sitl_harness.py"),
            self.spawn_python("-c", sleeper, "gz", "ign", "signal", "design"),
            self.spawn_python("-c", sleeper, "/home/x/PX4-Autopilot", "PX4_SIM_MODEL=gz_rc_cessna"),
            self.spawn_argv0("gzip"),
            self.spawn_argv0("px4_helper"),
        }

        self.assertEqual(pids & self.matched(), set())


class TestCoreStartupCleanupRun(unittest.TestCase):

    @patch("QGCR.core.startup_cleanup.time.sleep")
    @patch("QGCR.core.startup_cleanup.glob.glob", return_value=[])
    @patch("QGCR.core.startup_cleanup.subprocess.run")
    def test_run_full_cleanup_uses_patterns(self, run, _glob, _sleep):
        run.return_value.stdout = ""

        StartupCleanup.run_full_cleanup()

        pkill_calls = [c.args[0] for c in run.call_args_list if c.args[0][0] == "pkill"]
        self.assertEqual(
            pkill_calls,
            [["pkill", "-9", "-f", p] for p in StartupCleanup.kill_patterns()],
        )
        for _, _, _, pattern in pkill_calls:
            self.assertTrue(pattern.startswith("^"), pattern)


if __name__ == "__main__":
    unittest.main()
