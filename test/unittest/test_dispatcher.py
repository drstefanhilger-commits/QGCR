# === PFAD-B FULL FILE: QGCR/test/unittest/test_dispatcher.py ===

import unittest
from types import SimpleNamespace

from QGCR.communication.dispatcher import Dispatcher
from QGCR.test.unittest.fake_mavlink import make_msg


class RecordingService:
    def __init__(self):
        self.handled = []

    def on_message(self, msg_type, msg):
        self.handled.append((msg_type, msg))


class FailingService:
    def on_message(self, msg_type, msg):
        raise RuntimeError("boom")


def make_model(**services):
    names = ("mission_ms", "upload_ms", "home_ms", "takeoff", "param_sync")
    return SimpleNamespace(**{n: services.get(n) for n in names})


class TestDispatcher(unittest.TestCase):

    def test_routes_message_to_all_services(self):
        services = {n: RecordingService() for n in
                    ("mission_ms", "upload_ms", "home_ms", "takeoff", "param_sync")}
        dispatcher = Dispatcher(make_model(**services))

        msg = make_msg("MISSION_COUNT", count=3)
        dispatcher.dispatch(msg)

        for svc in services.values():
            self.assertEqual(svc.handled, [("MISSION_COUNT", msg)])

    def test_skips_missing_services(self):
        home = RecordingService()
        dispatcher = Dispatcher(make_model(home_ms=home))

        msg = make_msg("HOME_POSITION")
        dispatcher.dispatch(msg)

        self.assertEqual(home.handled, [("HOME_POSITION", msg)])

    def test_skips_services_without_on_message(self):
        takeoff = RecordingService()
        dispatcher = Dispatcher(make_model(mission_ms=object(), takeoff=takeoff))

        msg = make_msg("COMMAND_ACK")
        dispatcher.dispatch(msg)

        self.assertEqual(takeoff.handled, [("COMMAND_ACK", msg)])

    def test_error_in_one_service_does_not_stop_others(self):
        upload = RecordingService()
        dispatcher = Dispatcher(make_model(mission_ms=FailingService(), upload_ms=upload))

        msg = make_msg("MISSION_REQUEST_INT", seq=0)
        dispatcher.dispatch(msg)

        self.assertEqual(upload.handled, [("MISSION_REQUEST_INT", msg)])

    def test_no_services(self):
        dispatcher = Dispatcher(make_model())
        dispatcher.dispatch(make_msg("UNKNOWN"))


if __name__ == "__main__":
    unittest.main()
