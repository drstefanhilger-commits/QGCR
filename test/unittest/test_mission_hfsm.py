# === PFAD-B FULL FILE: QGCR/test/unittest/test_mission_hfsm.py ===

import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

from pymavlink import mavutil

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.mission.mission_hfsm import MissionHFSM
from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.states.main_state import MainState


def item(seq, lat=47.0, lon=8.0, alt=30.0, command=16):
    return SimpleNamespace(seq=seq, command=command, x=int(lat * 1e7), y=int(lon * 1e7), z=alt)


class TestMissionHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True
        self.model.active_tab = "Mission"

        self.ms = MagicMock()
        self.ms.last_error = None
        self.ms.upload.return_value = True
        self.ms.download.return_value = [item(0), item(1, 47.1, 8.1, 40)]
        self.model.mission_ms = self.ms

        self.fsm = MissionHFSM(self.model)
        self.fsm.on_update()                      # enter

    def tick_until_idle(self, timeout=2.0):
        deadline = time.time() + timeout
        state = self.fsm.on_update()
        while self.model.hfsm_sub != "IDLE" and time.time() < deadline:
            time.sleep(0.01)
            state = self.fsm.on_update()
        return state

    # --------------------------------------------------------
    # Grundverhalten
    # --------------------------------------------------------
    def test_enter_sets_state(self):
        self.assertEqual(self.model.hfsm_main, "MISSION")
        self.assertEqual(self.model.hfsm_sub, "IDLE")

    def test_home_tab_goes_ready(self):
        self.model.active_tab = "Home"
        self.assertEqual(self.fsm.on_update(), MainState.READY)

    def test_log_tab_stays_mission(self):
        self.model.active_tab = "Log"
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

    def test_reset_event_goes_reset(self):
        self.model.hfsm_events.append("RESET")
        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    def test_connection_lost_goes_reset(self):
        self.model.px4_connected = False
        self.assertEqual(self.fsm.on_update(), MainState.RESET)

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------
    def test_download_writes_mission_in_degrees(self):
        self.model.hfsm_events.append("MISSION_DOWNLOAD")

        self.assertEqual(self.tick_until_idle(), MainState.MISSION)

        self.ms.download.assert_called_once()
        self.assertTrue(self.model.mission.ready)
        self.assertTrue(self.model.mission_loaded)
        self.assertEqual(self.model.mission.count, 2)
        self.assertEqual(self.model.mission.items[1],
                         {"seq": 1, "command": 16, "x": 47.1, "y": 8.1, "z": 40})
        self.assertEqual(self.model.mission_status, "Download OK (2 Items)")

    def test_failed_download_keeps_old_mission(self):
        self.model.add_mission_item(0, 16, 1.0, 2.0, 3.0)
        self.model.mission.ready = True
        self.ms.download.return_value = [item(0)]
        self.ms.last_error = "Timeout (MISSION_ITEM_INT seq=1)"

        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.tick_until_idle()

        self.assertEqual(self.model.mission.items, [{"seq": 0, "command": 16, "x": 1.0, "y": 2.0, "z": 3.0}])
        self.assertEqual(self.model.mission_status,
                         "Download FEHLGESCHLAGEN: Timeout (MISSION_ITEM_INT seq=1)")

    def test_download_exception(self):
        self.ms.download.side_effect = RuntimeError("boom")
        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.tick_until_idle()

        self.assertEqual(self.model.mission_status, "Download FEHLGESCHLAGEN: boom")

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------
    def test_upload_sends_loaded_items_and_stores_them(self):
        items = [item(0), item(1, 47.2, 8.2, 50)]
        self.model.mission_upload_items = items
        self.model.hfsm_events.append("MISSION_UPLOAD")

        self.tick_until_idle()

        self.ms.upload.assert_called_once_with(items, cancel=ANY)
        self.assertEqual(self.model.mission.count, 2)
        self.assertEqual(self.model.mission_status, "Upload OK (2 Items)")

    def test_upload_failed(self):
        self.model.mission_upload_items = [item(0)]
        self.ms.upload.return_value = False
        self.ms.last_error = "PX4 lehnt Mission ab (MAV_MISSION_RESULT 1)"
        self.model.hfsm_events.append("MISSION_UPLOAD")

        self.tick_until_idle()

        self.assertEqual(self.model.mission.count, 0)
        self.assertEqual(self.model.mission_status,
                         "Upload FEHLGESCHLAGEN: PX4 lehnt Mission ab (MAV_MISSION_RESULT 1)")

    def test_upload_without_plan(self):
        self.model.hfsm_events.append("MISSION_UPLOAD")
        self.fsm.on_update()

        self.ms.upload.assert_not_called()
        self.assertEqual(self.model.mission_status, "Upload: keine Mission geladen")

    def test_transfer_without_service(self):
        self.model.mission_ms = None
        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.fsm.on_update()

        self.assertEqual(self.model.hfsm_sub, "IDLE")
        self.assertEqual(self.model.mission_status, "Download: keine Verbindung zu PX4")

    # --------------------------------------------------------
    # Laufender Transfer
    # --------------------------------------------------------
    def blocking_download(self):
        release = threading.Event()
        self.ms.download.side_effect = lambda **kw: (release.wait(2), [item(0)])[1]
        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.fsm.on_update()
        self.assertEqual(self.model.hfsm_sub, "DOWNLOAD")
        return release

    def test_runs_in_worker_thread_without_blocking_tick(self):
        release = self.blocking_download()

        start = time.time()
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)
        self.assertLess(time.time() - start, 0.5)

        release.set()
        self.tick_until_idle()
        self.assertEqual(self.model.mission.count, 1)

    def test_second_transfer_is_ignored_while_busy(self):
        release = self.blocking_download()

        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.fsm.on_update()

        release.set()
        self.tick_until_idle()
        self.ms.download.assert_called_once()

    def test_home_tab_is_deferred_until_transfer_done(self):
        release = self.blocking_download()

        self.model.active_tab = "Home"
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

        release.set()
        self.assertEqual(self.tick_until_idle(), MainState.READY)
        self.assertEqual(self.model.mission.count, 1)

    def test_reset_while_busy_goes_reset(self):
        release = self.blocking_download()

        self.model.hfsm_events.append("RESET")
        self.assertEqual(self.fsm.on_update(), MainState.RESET)
        release.set()

    # --------------------------------------------------------
    # Stop (MISSION_STOP)
    # --------------------------------------------------------
    def cancellable_download(self):
        """download() wartet, bis der übergebene cancel gesetzt wird."""
        self.cancels = []

        def download(cancel=None):
            self.cancels.append(cancel)
            cancel.wait(2)
            self.ms.last_error = MissionMicroService.CANCELLED
            return [item(0)]

        self.ms.download.side_effect = download
        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.fsm.on_update()

    def test_stop_cancels_running_transfer(self):
        self.model.add_mission_item(0, 16, 1.0, 2.0, 3.0)
        self.cancellable_download()

        self.model.hfsm_events.append("MISSION_STOP")
        self.fsm.on_update()
        self.assertEqual(self.model.mission_status, "Download wird abgebrochen …")
        self.assertTrue(self.cancels[0].is_set())

        self.tick_until_idle()
        self.assertEqual(self.model.mission_status, "Download abgebrochen")
        self.assertEqual(self.model.mission.items, [{"seq": 0, "command": 16, "x": 1.0, "y": 2.0, "z": 3.0}])

    def test_stop_cancels_upload(self):
        def upload(items, cancel=None):
            cancel.wait(2)
            self.ms.last_error = MissionMicroService.CANCELLED
            return False

        self.ms.upload.side_effect = upload
        self.model.mission_upload_items = [item(0)]
        self.model.hfsm_events.append("MISSION_UPLOAD")
        self.fsm.on_update()

        self.model.hfsm_events.append("MISSION_STOP")
        self.tick_until_idle()

        self.assertEqual(self.model.mission_status, "Upload abgebrochen")
        self.assertEqual(self.model.mission.count, 0)

    def test_stop_without_transfer_is_ignored(self):
        self.model.hfsm_events.append("MISSION_STOP")
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)
        self.assertEqual(self.model.mission_status, "-")
        self.assertIn("[QGCR] [MissionHFSM] Stop ignoriert: kein Transfer aktiv", self.model.qgcr_logs())

    def test_each_transfer_gets_fresh_cancel(self):
        self.cancellable_download()
        self.model.hfsm_events.append("MISSION_STOP")
        self.tick_until_idle()

        self.ms.last_error = None
        self.ms.download.side_effect = None
        self.ms.download.return_value = [item(0)]
        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.tick_until_idle()

        cancel = self.ms.download.call_args.kwargs["cancel"]
        self.assertIsNot(cancel, self.cancels[0])
        self.assertFalse(cancel.is_set())
        self.assertEqual(self.model.mission_status, "Download OK (1 Items)")

    def test_home_tab_after_cancel_goes_ready(self):
        self.cancellable_download()
        self.model.active_tab = "Home"
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

        self.model.hfsm_events.append("MISSION_STOP")
        self.assertEqual(self.tick_until_idle(), MainState.READY)

    # --------------------------------------------------------
    # Missionsstart vom Boden (MISSION_START)
    # --------------------------------------------------------
    def ready_to_start(self):
        conn = MagicMock()
        conn.master.target_system = 1
        conn.master.target_component = 1
        self.model.connection = conn
        self.model.add_mission_item(0, 22, 47.0, 8.0, 20.0)
        self.model.mission.ready = True
        return conn

    def test_start_sends_mission_start(self):
        conn = self.ready_to_start()
        self.model.hfsm_events.append("MISSION_START")

        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

        msg = conn.send.call_args[0][0]
        self.assertEqual(msg.command, mavutil.mavlink.MAV_CMD_MISSION_START)
        self.assertEqual(self.model.hfsm_sub, "START")
        self.assertEqual(self.model.mission_status, "Missionsstart gesendet …")

    def test_start_goes_airborne_when_armed_in_auto_mission(self):
        self.ready_to_start()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        self.model.px4_armed = True
        self.model.px4_mode = "AUTO.MISSION"

        self.assertEqual(self.fsm.on_update(), MainState.AIRBORNE)
        self.assertTrue(self.model.mission_running)
        self.assertEqual(self.model.mission_status, "Mission läuft")

    def test_start_rejected_after_timeout(self):
        self.ready_to_start()
        with patch("QGCR.states.mission.mission_hfsm.time.time", return_value=1000.0):
            self.model.hfsm_events.append("MISSION_START")
            self.fsm.on_update()

        with patch("QGCR.states.mission.mission_hfsm.time.time", return_value=1011.0):
            self.assertEqual(self.fsm.on_update(), MainState.MISSION)

        self.assertEqual(self.model.hfsm_sub, "IDLE")
        self.assertFalse(self.model.mission_running)
        self.assertTrue(self.model.mission_status.startswith("Missionsstart abgelehnt"))

    def test_start_without_mission(self):
        conn = self.ready_to_start()
        self.model.mission.ready = False
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        conn.send.assert_not_called()
        self.assertEqual(self.model.mission_status, "Start: keine Mission (erst hoch- oder herunterladen)")

    def test_start_without_connection(self):
        self.model.add_mission_item(0, 22, 47.0, 8.0, 20.0)
        self.model.mission.ready = True
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        self.assertEqual(self.model.mission_status, "Start: keine Verbindung zu PX4")

    def test_home_tab_waits_while_starting(self):
        self.ready_to_start()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        self.model.active_tab = "Home"
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)

    def test_no_transfer_while_starting(self):
        self.ready_to_start()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        self.model.hfsm_events.append("MISSION_DOWNLOAD")
        self.fsm.on_update()
        self.ms.download.assert_not_called()

    def test_stop_while_starting_is_ignored(self):
        self.ready_to_start()
        self.model.hfsm_events.append("MISSION_START")
        self.fsm.on_update()

        self.model.hfsm_events.append("MISSION_STOP")
        self.assertEqual(self.fsm.on_update(), MainState.MISSION)
        self.assertEqual(self.model.hfsm_sub, "START")


if __name__ == "__main__":
    unittest.main()
