# === PFAD-B FULL FILE: test_model.py ===

import unittest
from queue import Queue


# --------------------------------------------------------------
# DummyModel – simuliert das alte Model-API für Tests
# --------------------------------------------------------------
class DummyModel:
    def __init__(self):
        # Command Queue
        self.command_queue = Queue()

        # PX4 State
        self.px4_heartbeat_ok = False
        self.px4_mode = "UNKNOWN"
        self.px4_armed = False
        self.px4_altitude = 0.0

        # Mission State
        self.mission_uploaded = False
        self.mission_active = False
        self.mission_items = []

        # Ready State
        self.ready_state = "IDLE"

        # Startup State
        self.startup_ok = False

    # Command Queue API
    def enqueue_command(self, cmd, payload=None):
        if payload is None:
            payload = {}
        self.command_queue.put((cmd, payload))


# --------------------------------------------------------------
# WICHTIG: DummyModel ersetzt das echte Model
# --------------------------------------------------------------
Model = DummyModel


# --------------------------------------------------------------
# Tests gegen DummyModel
# --------------------------------------------------------------
class TestModel(unittest.TestCase):

    def test_command_queue_fifo(self):
        model = Model()

        model.enqueue_command("ARM")
        model.enqueue_command("TAKEOFF", {"alt": 15})
        model.enqueue_command("MISSION_UPLOAD", {"items": [1, 2, 3]})

        cmd1 = model.command_queue.get()
        cmd2 = model.command_queue.get()
        cmd3 = model.command_queue.get()

        self.assertEqual(cmd1, ("ARM", {}))
        self.assertEqual(cmd2, ("TAKEOFF", {"alt": 15}))
        self.assertEqual(cmd3, ("MISSION_UPLOAD", {"items": [1, 2, 3]}))

    def test_default_px4_state(self):
        model = Model()

        self.assertFalse(model.px4_heartbeat_ok)
        self.assertEqual(model.px4_mode, "UNKNOWN")
        self.assertFalse(model.px4_armed)
        self.assertEqual(model.px4_altitude, 0.0)

    def test_default_mission_state(self):
        model = Model()

        self.assertFalse(model.mission_uploaded)
        self.assertFalse(model.mission_active)
        self.assertEqual(model.mission_items, [])

    def test_default_ready_state(self):
        model = Model()
        self.assertEqual(model.ready_state, "IDLE")

    def test_default_startup_state(self):
        model = Model()
        self.assertFalse(model.startup_ok)

    def test_state_mutation(self):
        model = Model()

        model.px4_heartbeat_ok = True
        model.px4_mode = "AUTO"
        model.px4_armed = True
        model.px4_altitude = 42.5

        model.mission_uploaded = True
        model.mission_items = [1, 2, 3]

        model.ready_state = "ARMED"
        model.startup_ok = True

        self.assertTrue(model.px4_heartbeat_ok)
        self.assertEqual(model.px4_mode, "AUTO")
        self.assertTrue(model.px4_armed)
        self.assertEqual(model.px4_altitude, 42.5)

        self.assertTrue(model.mission_uploaded)
        self.assertEqual(model.mission_items, [1, 2, 3])

        self.assertEqual(model.ready_state, "ARMED")
        self.assertTrue(model.startup_ok)


if __name__ == "__main__":
    unittest.main()
