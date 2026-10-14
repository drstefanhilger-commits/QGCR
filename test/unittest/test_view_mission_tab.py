# === PFAD-B FULL FILE: QGCR/test/unittest/test_view_mission_tab.py ===

import unittest
import tkinter as tk
from unittest.mock import MagicMock

from QGCR.view.mission_tab import MissionTab


class TestViewMissionTab(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.ctrl = MagicMock()
        self.tab = MissionTab(self.root, controller=self.ctrl)

    def tearDown(self):
        self.tab.destroy()
        self.root.destroy()

    def data(self, waypoints):
        return {
            "home_text": "Home: 47.39774, 8.54559, 488.0 m",
            "mission_text": f"Mission: {len(waypoints)} Waypoints",
            "waypoints": waypoints,
            "status_text": "Status: Download OK",
        }

    def test_buttons_start_disabled(self):
        for btn in (self.tab.btn_upload, self.tab.btn_download, self.tab.btn_stop):
            self.assertEqual(str(btn["state"]), "disabled")

    def test_set_enabled(self):
        self.tab.set_enabled(upload=True, download=True, stop=False)

        self.assertEqual(str(self.tab.btn_upload["state"]), "normal")
        self.assertEqual(str(self.tab.btn_download["state"]), "normal")
        self.assertEqual(str(self.tab.btn_stop["state"]), "disabled")

    def test_upload_button_requests_plan(self):
        self.tab.set_enabled(upload=True, download=True, stop=False)
        self.tab.btn_upload.invoke()
        self.ctrl.request_mission_upload.assert_called_once_with()

    def test_download_button_sends_event(self):
        self.tab.set_enabled(upload=True, download=True, stop=False)
        self.tab.btn_download.invoke()
        self.ctrl.handle_button_event.assert_called_once_with("MISSION_DOWNLOAD")

    def test_start_button(self):
        self.assertEqual(str(self.tab.btn_start["state"]), "disabled")

        self.tab.set_enabled(upload=True, download=True, stop=False, start=True)
        self.assertEqual(str(self.tab.btn_start["state"]), "normal")

        self.tab.btn_start.invoke()
        self.ctrl.handle_button_event.assert_called_once_with("MISSION_START")

    def test_stop_button_sends_event(self):
        self.tab.set_enabled(upload=False, download=False, stop=True)
        self.tab.btn_stop.invoke()
        self.ctrl.handle_button_event.assert_called_once_with("MISSION_STOP")

    def test_show_mission(self):
        self.tab.show_mission(self.data(["00: A", "01: B"]))

        self.assertEqual(self.tab.lbl_home["text"], "Home: 47.39774, 8.54559, 488.0 m")
        self.assertEqual(self.tab.lbl_mission["text"], "Mission: 2 Waypoints")
        self.assertEqual(self.tab.lbl_status["text"], "Status: Download OK")
        self.assertEqual(list(self.tab.listbox.get(0, "end")), ["00: A", "01: B"])

    def test_show_mission_keeps_selection_when_unchanged(self):
        self.tab.show_mission(self.data(["00: A", "01: B"]))
        self.tab.listbox.selection_set(1)

        self.tab.show_mission(self.data(["00: A", "01: B"]))
        self.assertEqual(self.tab.listbox.curselection(), (1,))

        self.tab.show_mission(self.data(["00: C"]))
        self.assertEqual(list(self.tab.listbox.get(0, "end")), ["00: C"])


if __name__ == "__main__":
    unittest.main()
