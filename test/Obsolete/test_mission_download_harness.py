# === PFAD-B FULL FILE: QGCR/test/test_mission_download_harness.py ===

import unittest
from pymavlink import mavutil

from QGCR.model.model import Model
from QGCR.services.mission_download_service import MissionDownloadService
from QGCR.states.startup.subfsms.startup_mission_fsm import StartupMissionFSM
from QGCR.states.startup.startup_substate import StartupSubState as SubState


# ------------------------------------------------------------
# Fake MAVLink-Verbindung (kein UDP, kein Socket)
# ------------------------------------------------------------
class FakeMav:
    def __init__(self):
        self.sent_messages = []

        class MavWriter:
            def __init__(self, outer):
                self.outer = outer

            def send(self, msg):
                self.outer.sent_messages.append(msg)

        self.mav = MavWriter(self)


# ------------------------------------------------------------
# Fake Dispatcher (ruft nur registrierte Handler auf)
# ------------------------------------------------------------
class FakeDispatcher:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, msg_type, fn):
        self.handlers[msg_type] = fn

    def inject(self, msg_type, msg):
        """Simuliert eingehende MAVLink-Nachrichten."""
        if msg_type in self.handlers:
            self.handlers[msg_type](msg)


# ------------------------------------------------------------
# Test-Harness
# ------------------------------------------------------------
class TestMissionDownloadHarness(unittest.TestCase):

    def test_mission_download_pipeline(self):
        # --- Setup ---
        model = Model()
        fake_mav = FakeMav()
        dispatcher = FakeDispatcher()

        service = MissionDownloadService(fake_mav, model)

        # Dispatcher registriert Handler
        dispatcher.register_handler("MISSION_COUNT", service.on_mission_count)
        dispatcher.register_handler("MISSION_ITEM_INT", service.on_mission_item_int)

        # Model-Callback setzen
        model.cb_on_startup_mission = service.start_download

        # FSM instanzieren
        fsm = StartupMissionFSM(model)

        # --- 1) FSM betritt STARTUP_MISSION ---
        fsm.on_update()

        # Erwartung: MISSION_REQUEST_LIST wurde gesendet
        self.assertEqual(len(fake_mav.sent_messages), 1)
        self.assertIsInstance(
            fake_mav.sent_messages[0],
            mavutil.mavlink.MAVLink_mission_request_list_message
        )

        # --- 2) PX4 antwortet mit MISSION_COUNT ---
        msg_count = mavutil.mavlink.MAVLink_mission_count_message(
            target_system=255,
            target_component=0,
            count=3
        )
        dispatcher.inject("MISSION_COUNT", msg_count)

        # Erwartung: MISSION_REQUEST(seq=0) wurde gesendet
        self.assertEqual(len(fake_mav.sent_messages), 2)
        self.assertEqual(fake_mav.sent_messages[1].seq, 0)

        # --- 3) PX4 sendet drei Mission-Items ---
        for seq in range(3):
            msg_item = mavutil.mavlink.MAVLink_mission_item_int_message(
                target_system=255,
                target_component=0,
                seq=seq,
                frame=0,
                command=16,
                current=0,
                autocontinue=1,
                param1=0, param2=0, param3=0, param4=0,
                x=470000000 + seq,
                y=80000000 + seq,
                z=10.0 + seq
            )
            dispatcher.inject("MISSION_ITEM_INT", msg_item)

        # Erwartung: Mission ist geladen
        self.assertTrue(model.mission_loaded)
        self.assertEqual(len(model.mission_waypoints), 3)

        # --- 4) FSM erkennt Fertigstellung ---
        next_state = fsm.on_update()
        self.assertEqual(next_state, SubState.STARTUP_OK)


if __name__ == "__main__":
    unittest.main()
