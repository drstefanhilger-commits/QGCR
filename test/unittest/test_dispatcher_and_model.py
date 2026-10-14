# === PFAD-B FULL FILE: QGCR/test/unittest/test_dispatcher_and_model.py ===

import unittest

from QGCR.communication.dispatcher import Dispatcher
from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.fake_mavlink import make_msg


class RecordingService:
    def __init__(self):
        self.handled = []

    def on_message(self, msg_type, msg):
        self.handled.append((msg_type, msg))


class TestDispatcherAndModel(unittest.TestCase):

    def test_default_null_services_are_ignored(self):
        """Model startet mit _NullService-Platzhaltern ohne on_message()."""
        dispatcher = Dispatcher(DummyModel())
        dispatcher.dispatch(make_msg("HEARTBEAT"))

    def test_model_aliases_receive_messages(self):
        model = DummyModel()
        model.mission_ms = RecordingService()
        model.takeoff = RecordingService()
        dispatcher = Dispatcher(model)

        msg = make_msg("COMMAND_ACK", command=22, result=0)
        dispatcher.dispatch(msg)

        self.assertEqual(model.mission_ms.handled, [("COMMAND_ACK", msg)])
        self.assertEqual(model.takeoff.handled, [("COMMAND_ACK", msg)])


if __name__ == "__main__":
    unittest.main()
