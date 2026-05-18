# === PFAD-B FULL FILE: test_dispatcher_and_model.py ===

import unittest

from QGCR.communication.dispatcher import Dispatcher
from QGCR.model.model import Model


# ----------------------------------------------------------------------
# Kompatible Dummy FSMs
# ----------------------------------------------------------------------

class DummySubFSM:
    def __init__(self, name):
        self.name = name
        self.handled = []

    def on_message(self, msg_type, msg):
        self.handled.append((msg_type, msg))

    def on_update(self):
        pass


class DummyFSM:
    def __init__(self, name):
        self.name = name
        self.active = DummySubFSM(name + "_SUB")

    def on_message(self, msg_type, msg):
        self.active.on_message(msg_type, msg)

    def on_update(self):
        pass


# ----------------------------------------------------------------------
# Testklasse
# ----------------------------------------------------------------------

class TestDispatcherAndModel(unittest.TestCase):

    # --------------------------------------------------------------
    # 1) Model CommandQueue existiert NICHT MEHR → Test entfernt
    # --------------------------------------------------------------
    def test_model_command_queue(self):
        """
        Dieser Test entfällt, da das Model keine CommandQueue mehr besitzt.
        """
        self.assertTrue(True)

    # --------------------------------------------------------------
    # 2) Dispatcher routet Messages korrekt
    # --------------------------------------------------------------
    def test_dispatcher_routing(self):
        model = Model()
        dispatcher = Dispatcher(model)

        startup = DummyFSM("STARTUP")
        ready = DummyFSM("READY")

        dispatcher.subscribe(startup, "HEARTBEAT")

        dispatcher.route_message("HEARTBEAT", {"foo": 1})
        dispatcher.on_update()

        self.assertEqual(startup.active.handled, [("HEARTBEAT", {"foo": 1})])
        self.assertEqual(ready.active.handled, [])

    # --------------------------------------------------------------
    # 3) Dispatcher + Model Integration
    # --------------------------------------------------------------
    def test_dispatcher_model_integration(self):
        model = Model()
        dispatcher = Dispatcher(model)

        startup = DummyFSM("STARTUP")
        dispatcher.subscribe(startup, "PX4_OK")

        # Dispatcher verarbeitet Event
        dispatcher.route_message("PX4_OK", {})
        dispatcher.on_update()

        self.assertEqual(startup.active.handled, [("PX4_OK", {})])


if __name__ == "__main__":
    unittest.main()

