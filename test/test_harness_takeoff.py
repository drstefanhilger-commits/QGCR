# === PFAD-B FULL FILE: QGCR/test/test_harness_takeoff.py ===

import time
import unittest
from types import SimpleNamespace

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.communication.microservices.takeoff_microservice import TakeoffMicroService


# ------------------------------------------------------------
# Fake Model (minimal, aber realistisch)
# ------------------------------------------------------------
class FakeModel:
    def __init__(self):
        self.px4_mode = None
        self.services = SimpleNamespace()
        self.telemetry_log = []
        self.heartbeat_log = []

    def on_heartbeat(self, msg):
        self.heartbeat_log.append(msg)

    def update_vehicle_position(self, lat, lon, alt):
        self.telemetry_log.append(("pos", lat, lon, alt))

    def update_home_position(self, lat, lon, alt):
        self.telemetry_log.append(("home", lat, lon, alt))

    def update_status(self, text):
        self.telemetry_log.append(("status", text))

    def on_command_ack(self, msg):
        self.telemetry_log.append(("ack", msg.command))


# ------------------------------------------------------------
# Fake MAVLink Master (kompatibel mit Connection + MicroService)
# ------------------------------------------------------------
class FakeMav:
    def __init__(self, parent):
        self.parent = parent

    def command_long_send(self, target_system, target_component, cmd, *args):
        self.parent.sent_commands.append((cmd, target_system, target_component, args))


class FakeMaster:
    def __init__(self):
        self.sent_commands = []
        self.sent_modes = []
        self.mav = FakeMav(self)

    def recv_match(self, *args, **kwargs):
        return None  # Connection worker will see no real MAVLink

    def set_mode(self, mode_name):
        self.sent_modes.append(mode_name)


# ------------------------------------------------------------
# Fake Connection (ersetzt echten UDP-Socket)
# ------------------------------------------------------------
class FakeConnection(Connection):
    def connect(self):
        # Kein echter Socket, nur FakeMaster
        self.master = FakeMaster()

        # Worker-Threads NICHT starten
        self._worker = None
        self._gcs_hb_thread = None


# ------------------------------------------------------------
# Fake MAVLink Messages
# ------------------------------------------------------------
def make_heartbeat(armed=False):
    msg = SimpleNamespace()
    msg.get_type = lambda: "HEARTBEAT"
    msg.get_srcSystem = lambda: 1
    msg.base_mode = 128 if armed else 0
    return msg


def make_global_position_int(relative_alt_m):
    msg = SimpleNamespace()
    msg.get_type = lambda: "GLOBAL_POSITION_INT"
    msg.relative_alt = int(relative_alt_m * 1000)
    msg.lat = 0
    msg.lon = 0
    msg.alt = int(relative_alt_m * 1000)
    return msg


# ------------------------------------------------------------
# Minimal FSM für den Harness-Test
# ------------------------------------------------------------
class FakeTakeoffFSM:
    def __init__(self, model):
        self.model = model
        self.service = model.services.takeoff

    def start(self):
        self.service.start()

    def tick(self):
        self.service.tick()


# ------------------------------------------------------------
# HARNESS TEST
# ------------------------------------------------------------
class TestHarnessTakeoff(unittest.TestCase):

    def test_end_to_end_takeoff(self):
        # Model + Dispatcher + Connection
        model = FakeModel()
        dispatcher = Dispatcher(model)
        conn = FakeConnection(model, dispatcher)
        conn.connect()

        # MicroService registrieren
        model.services.takeoff = TakeoffMicroService(
            connection=conn,
            model=model,
            target_altitude=10.0,
            arm_timeout=0.3,
            mode_timeout=0.3,
            takeoff_timeout=0.3,
            climb_timeout=0.3,
        )

        # FSM
        fsm = FakeTakeoffFSM(model)
        fsm.start()

        # Tick 1: ARM senden
        fsm.tick()
        self.assertEqual(model.services.takeoff._state, "WAIT_ARMED")

        # HEARTBEAT (armed)
        hb = make_heartbeat(armed=True)
        dispatcher.route_message("HEARTBEAT", hb)

        # Tick 2: WAIT_ARMED → SET_MODE
        fsm.tick()
        self.assertEqual(model.services.takeoff._state, "SET_MODE")

        # Tick 3: SET_MODE → WAIT_MODE
        fsm.tick()
        self.assertEqual(model.services.takeoff._state, "WAIT_MODE")

        # Mode-Bestätigung
        model.px4_mode = "AUTO.TAKEOFF"
        dispatcher.route_message("HEARTBEAT", hb)

        # Tick 4: WAIT_MODE → SEND_TAKEOFF
        fsm.tick()
        self.assertEqual(model.services.takeoff._state, "SEND_TAKEOFF")

        # Tick 5: SEND_TAKEOFF → WAIT_CLIMB
        fsm.tick()
        self.assertEqual(model.services.takeoff._state, "WAIT_CLIMB")

        # Höhenanstieg simulieren
        pos = make_global_position_int(8.0)
        dispatcher.route_message("GLOBAL_POSITION_INT", pos)

        # Tick 6: WAIT_CLIMB → DONE
        fsm.tick()
        self.assertTrue(model.services.takeoff.done)
        self.assertIsNone(model.services.takeoff.error)


if __name__ == "__main__":
    unittest.main()
