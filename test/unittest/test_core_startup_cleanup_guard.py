# === PFAD-B FULL FILE: QGCR/test/unittest/test_core_startup_cleanup_guard.py ===

import os
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from QGCR.core.startup_cleanup import StartupCleanup
from QGCR.main import Application
from QGCR.test.unittest import sitl_helper


class Decoys:
    """Harmlose Prozesse, die wie QGCR / PX4 aussehen (sleep mit anderem Namen)."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.procs = []

    def qgcr(self):
        p = subprocess.Popen(["bash", "-c", "exec -a 'python3 -m QGCR.main' sleep 30"])
        self.procs.append(p)
        return p.pid

    def px4(self):
        link = os.path.join(self.tmp.name, "px4")
        if not os.path.exists(link):
            os.symlink("/bin/sleep", link)
        p = subprocess.Popen([link, "30"])
        self.procs.append(p)
        return p.pid

    def close(self):
        for p in self.procs:
            p.kill()
            p.wait()
        self.tmp.cleanup()


def real_session_running():
    try:
        sitl_helper.assert_no_foreign_session()
        return False
    except RuntimeError:
        return True


class TestCoreStartupCleanupGuard(unittest.TestCase):

    def setUp(self):
        self.decoys = Decoys()
        self.addCleanup(self.decoys.close)

    def test_find_other_qgcr(self):
        pid = self.decoys.qgcr()
        time.sleep(0.3)
        pids = [p for p, _ in StartupCleanup.find_other_qgcr()]
        self.assertIn(pid, pids)
        self.assertNotIn(os.getpid(), pids)

    def test_test_runner_is_not_qgcr(self):
        """Ein Prozess wie 'python -m unittest QGCR.test.unittest.test_main' ist keine QGCR."""
        p = subprocess.Popen(["bash", "-c", "exec -a 'python3 -m unittest QGCR.test.unittest.test_main' sleep 30"])
        self.decoys.procs.append(p)
        time.sleep(0.3)
        self.assertNotIn(p.pid, [pid for pid, _ in StartupCleanup.find_other_qgcr()])

    @patch.object(StartupCleanup, "run_full_cleanup")
    @patch.object(StartupCleanup, "find_other_qgcr", return_value=[(4242, "python3 -m QGCR.main")])
    def test_second_instance_refuses_before_cleanup(self, _find, cleanup):
        with self.assertRaisesRegex(RuntimeError, "QGCR läuft bereits \\(PID 4242\\)"):
            Application()
        cleanup.assert_not_called()

    def test_sitl_guard_detects_qgcr_and_px4(self):
        self.decoys.qgcr()
        self.decoys.px4()
        time.sleep(0.3)
        with self.assertRaises(RuntimeError) as ctx:
            sitl_helper.assert_no_foreign_session()
        self.assertIn("QGCR (PID", str(ctx.exception))
        self.assertIn("PX4 (PID", str(ctx.exception))

    def test_sitl_guard_passes_without_session(self):
        if real_session_running():
            self.skipTest("echte QGCR/PX4-Sitzung läuft")
        sitl_helper.assert_no_foreign_session()

    def test_px4sitl_start_refuses_and_kills_nothing(self):
        pid = self.decoys.px4()
        time.sleep(0.3)
        with patch.object(sitl_helper.PX4Sitl, "_kill_leftovers") as kill:
            with self.assertRaises(RuntimeError):
                sitl_helper.PX4Sitl().start()
            kill.assert_not_called()
        os.kill(pid, 0)                                   # Lockvogel lebt noch


if __name__ == "__main__":
    unittest.main()
