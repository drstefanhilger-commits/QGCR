# === PFAD-B FULL FILE: test_dispatcher.py ===

import unittest

from QGCR.communication.dispatcher import Dispatcher
from QGCR.model.model import Model


# ----------------------------------------------------------------------
# Kompatible Dummy FSM
# ----------------------------------------------------------------------

class DummyFSM:
    def __init__(self, name):
        self.name = name
        self.handled = []
        self.update_count = 0

    def on_message(self, msg_type, msg):
        self.handled.append((msg_type, msg))

    def on_update(self):
        self.update_count += 1


# ----------------------------------------------------------------------
# Testklasse
# ----------------------------------------------------------------------

class TestDispatcher(unittest.TestCase):

    # --------------------------------------------------------------
    # 1) Routing zu einem Subscriber
    # --------------------------------------------------------------
    def test_dispatcher_routes_items_to_subscriber(self):
        model = Model()
        dispatcher = Dispatcher(model)

        fsm = DummyFSM("FSM1")
        dispatcher.subscribe(fsm, "TEST")

        dispatcher.route_message("TEST", {"x": 1})
        dispatcher.on_update()

        self.assertEqual(fsm.handled, [("TEST", {"x": 1})])

    # --------------------------------------------------------------
    # 2) Unsubscribe funktioniert
    # --------------------------------------------------------------
    def test_dispatcher_unsubscribe(self):
        model = Model()
        dispatcher = Dispatcher(model)

        fsm = DummyFSM("FSM1")
        dispatcher.subscribe(fsm, "TEST")
        dispatcher.unsubscribe(fsm, "TEST")

        dispatcher.route_message("TEST", {"x": 1})
        dispatcher.on_update()

        self.assertEqual(fsm.handled, [])

    # --------------------------------------------------------------
    # 3) Mehrere Subscriber
    # --------------------------------------------------------------
    def test_dispatcher_multiple_subscribers(self):
        model = Model()
        dispatcher = Dispatcher(model)

        fsm1 = DummyFSM("FSM1")
        fsm2 = DummyFSM("FSM2")

        dispatcher.subscribe(fsm1, "PING")
        dispatcher.subscribe(fsm2, "PING")

        dispatcher.route_message("PING", 42)
        dispatcher.on_update()

        self.assertEqual(fsm1.handled, [("PING", 42)])
        self.assertEqual(fsm2.handled, [("PING", 42)])

    # --------------------------------------------------------------
    # 4) on_update() ruft jede FSM genau einmal auf
    # --------------------------------------------------------------
    def test_dispatcher_on_update_calls_each_fsm_once(self):
        model = Model()
        dispatcher = Dispatcher(model)

        fsm1 = DummyFSM("FSM1")
        fsm2 = DummyFSM("FSM2")

        dispatcher.subscribe(fsm1, "A")
        dispatcher.subscribe(fsm2, "B")

        dispatcher.on_update()

        self.assertEqual(fsm1.update_count, 1)
        self.assertEqual(fsm2.update_count, 1)

    # --------------------------------------------------------------
    # 5) Keine Subscriber → keine Fehler
    # --------------------------------------------------------------
    def test_dispatcher_no_subscribers(self):
        model = Model()
        dispatcher = Dispatcher(model)

        # Sollte einfach durchlaufen
        dispatcher.route_message("UNKNOWN", {})
        dispatcher.on_update()

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
