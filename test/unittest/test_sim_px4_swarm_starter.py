# === PFAD-B FULL FILE: QGCR/test/unittest/test_sim_px4_swarm_starter.py ===

import os
import queue
import tempfile
import time
import unittest
from unittest.mock import patch

from QGCR.sim.px4_swarm_starter import PX4SwarmStarter, PX4InstanceConfig
from QGCR.test.unittest.dummy_model import DummyModel


# Fake-PX4: "make px4_sitl gz_fake" schreibt ~500 KB auf stderr, dann DONE auf stdout
MAKEFILE = (
    "px4_sitl:\n"
    "\t@python3 -c \"import sys; [sys.stderr.write('E' * 99 + '\\n') for _ in range(5000)]; "
    "print('DONE', flush=True)\"\n"
    "gz_fake:\n"
    "\t@true\n"
    "stdin_check:\n"
    "\t@readlink /proc/self/fd/0\n"
)


@patch("builtins.print")
class TestSimPX4SwarmStarter(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with open(os.path.join(self.tmp.name, "Makefile"), "w") as f:
            f.write(MAKEFILE)
        self.cfg = PX4InstanceConfig(self.tmp.name, "gz_fake", instance_id=1, verbose=False)

    def tearDown(self):
        self.tmp.cleanup()

    def px4_logs(self, model, until, timeout=10):
        q = model.queue_registry.px4_log_queue
        lines = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                lines.append(q.get(timeout=0.1))
            except queue.Empty:
                continue
            if lines[-1] == until:
                break
        return lines

    def test_large_stderr_does_not_block_px4(self, _print):
        model = DummyModel()
        starter = PX4SwarmStarter([self.cfg], model=model)
        starter.start_all()

        proc = starter.processes[1]
        proc.wait(timeout=10)          # alter Code: blockiert (stderr-Pipe voll)
        self.assertEqual(proc.returncode, 0)

        lines = self.px4_logs(model, "[PX4-1] DONE")
        self.assertEqual(lines[-1], "[PX4-1] DONE")
        self.assertEqual(sum(1 for l in lines if l.startswith("[PX4-1] EEE")), 5000)

    def test_px4_does_not_inherit_terminal_stdin(self, _print):
        model = DummyModel()
        cfg = PX4InstanceConfig(self.tmp.name, "stdin_check", instance_id=1, verbose=False)
        starter = PX4SwarmStarter([cfg], model=model)
        starter.start_all()
        starter.processes[1].wait(timeout=10)

        # eigene Pipe – weder Terminal noch /dev/null (pxh würde bei EOF endlos Prompts ausgeben)
        lines = self.px4_logs(model, "never", timeout=3)
        stdin_lines = [l for l in lines if l.startswith("[PX4-1] /") or l.startswith("[PX4-1] pipe:")]
        self.assertEqual(len(stdin_lines), 1, lines)
        self.assertTrue(stdin_lines[0].startswith("[PX4-1] pipe:"), stdin_lines[0])

    def test_stop_closes_stdin(self, _print):
        cfg = PX4InstanceConfig(self.tmp.name, "gz_fake", instance_id=1, verbose=False)
        starter = PX4SwarmStarter([cfg], model=DummyModel())
        starter.start_all()
        proc = starter.processes[1]

        with patch("QGCR.sim.px4_swarm_starter.subprocess.run"):
            starter.stop_all()

        self.assertTrue(proc.stdin.closed)

    def test_without_logger_output_is_discarded(self, _print):
        starter = PX4SwarmStarter([self.cfg], model=None)
        starter.start_all()

        proc = starter.processes[1]
        proc.wait(timeout=10)

        self.assertEqual(proc.returncode, 0)
        self.assertIsNone(proc.stdout)
        self.assertIsNone(proc.stderr)


if __name__ == "__main__":
    unittest.main()
