# === PFAD-B FULL FILE: QGCR/test/unittest/test_mission_hfsm.py ===

import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.mission.mission_hfsm import MissionHFSM
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

        self.ms.upload.assert_called_once_with(items)
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
        self.ms.download.side_effect = lambda: (release.wait(2), [item(0)])[1]
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


if __name__ == "__main__":
    unittest.main()
