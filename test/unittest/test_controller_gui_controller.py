# === PFAD-B FULL FILE: QGCR/test/unittest/test_controller_gui_controller.py ===

import os
import unittest
from unittest.mock import MagicMock, patch

from QGCR.controller.gui_controller import GUIController
from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.plan_fixture import write_plan
from QGCR.sim.px4_swarm_starter import PX4InstanceConfig


class TestControllerGUIController(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.gui = GUIController(self.model, None, None, self.model.queue_registry)

    @patch("builtins.print")
    def test_home_tab_buttons_reach_hfsm_queue(self, _print):
        for event in ("ARM", "DISARM", "TAKEOFF", "LAND", "RESET"):
            self.gui.handle_button_event(event)

        self.assertEqual(list(self.model.hfsm_events),
                         ["ARM", "DISARM", "TAKEOFF", "LAND", "RESET"])

    @patch("builtins.print")
    def test_unknown_button_event_is_ignored(self, _print):
        self.gui.handle_button_event("ARMM")
        self.assertEqual(len(self.model.hfsm_events), 0)

    def test_process_gui_queue(self):
        window = MagicMock()
        self.gui.main_window = window
        gui = self.model.queue_registry.require("gui")

        gui.push(("telemetry", {"alt": 1.0}))
        gui.push(("status", "Home set: 47.39774, 8.54559, 488.0 m"))
        gui.push(("log", "READY_HEARTBEAT_LOST: Heartbeat lost"))
        gui.push(("state_update", {}))
        gui.push("kaputt")
        gui.push(("status", "ACK: 400 → 0"))

        self.gui.process_gui_queue()

        window.status_bar.set_message.assert_called_with("ACK: 400 → 0")
        self.assertEqual(window.status_bar.set_message.call_count, 2)
        self.assertEqual(
            [c.args[0] for c in window.log_tab.append_qgcr.call_args_list],
            ["[STATUS] Home set: 47.39774, 8.54559, 488.0 m",
             "READY_HEARTBEAT_LOST: Heartbeat lost",
             "[STATUS] ACK: 400 → 0"],
        )
        self.assertEqual(gui.pop_all(), [])

    def test_process_gui_queue_without_window_drains(self):
        self.model.queue_registry.require("gui").push(("status", "x"))
        self.gui.process_gui_queue()
        self.assertEqual(self.model.queue_registry.require("gui").pop_all(), [])

    def test_plot_data(self):
        m = self.model
        m.home_lat, m.home_lon = 47.0, 8.0
        m.vehicle_lat, m.vehicle_lon = 47.001, 8.0
        m.mission_track = [(47.0, 8.0), (47.001, 8.0)]
        m.add_mission_item(0, 22, 47.0, 8.0, 20.0)
        m.add_mission_item(1, 189, 0.0, 0.0, 0.0)          # DO_LAND_START ohne Position
        m.add_mission_item(2, 21, 47.002, 8.001, 0.0)

        data = self.gui.get_plot_data()
        self.assertEqual(data["waypoints"], [])            # Mission noch nicht "ready"
        self.assertIsNone(data["landing"])

        m.mission.ready = True
        data = self.gui.get_plot_data()
        self.assertEqual(data["track"], [(47.0, 8.0), (47.001, 8.0)])
        self.assertIsNot(data["track"], m.mission_track)   # Kopie
        self.assertEqual(data["start"], (47.0, 8.0))           # vor einer Mission: Home

        m.mission_start_point = (47.0005, 8.0005)               # nach Missionsstart
        m.home_lat, m.home_lon = 47.002, 8.001                  # Home später neu gesetzt
        self.assertEqual(self.gui.get_plot_data()["start"], (47.0005, 8.0005))
        self.assertEqual(data["vehicle"], (47.001, 8.0))
        self.assertEqual(data["landing"], (47.002, 8.001))
        self.assertEqual(data["waypoints"], [(47.0, 8.0), (47.002, 8.001)])

    def test_update_plot_draws(self):
        window = MagicMock()
        self.gui.main_window = window
        self.gui.update_plot()
        window.home_tab.canvas.draw.assert_called_once_with(self.gui.get_plot_data())

    def test_tab_changed_sets_active_tab(self):
        self.gui.on_tab_changed("Log")
        self.assertEqual(self.model.active_tab, "Log")


@patch("builtins.print")
class TestControllerGUIControllerMission(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.hfsm_main = "MISSION"
        self.model.hfsm_sub = "IDLE"
        self.gui = GUIController(self.model, None, None, self.model.queue_registry)
        self.path = write_plan()

    def tearDown(self):
        os.remove(self.path)

    def test_upload_loads_plan_and_sends_event(self, _print):
        self.gui.request_mission_upload(self.path)

        self.assertEqual(len(self.model.mission_upload_items), 3)
        self.assertEqual(self.model.mission_upload_file, self.path)
        self.assertEqual(list(self.model.hfsm_events), ["MISSION_UPLOAD"])

    def test_upload_only_in_mission(self, _print):
        self.model.hfsm_main = "READY"
        self.gui.request_mission_upload(self.path)

        self.assertIsNone(self.model.mission_upload_items)
        self.assertEqual(len(self.model.hfsm_events), 0)

    def test_upload_invalid_plan(self, _print):
        with open(self.path, "w") as f:
            f.write("{kein json")

        self.gui.request_mission_upload(self.path)

        self.assertEqual(len(self.model.hfsm_events), 0)
        self.assertTrue(self.model.mission_status.startswith("Plan-Datei fehlerhaft"))

    @patch("tkinter.filedialog.askopenfilename", return_value="")
    def test_upload_dialog_cancelled(self, _dialog, _print):
        self.gui.request_mission_upload()
        self.assertEqual(len(self.model.hfsm_events), 0)

    @patch("tkinter.filedialog.askopenfilename")
    def test_upload_dialog_selects_plan(self, dialog, _print):
        dialog.return_value = self.path
        self.gui.request_mission_upload()
        self.assertEqual(list(self.model.hfsm_events), ["MISSION_UPLOAD"])

    def test_view_data_with_mission_and_status(self, _print):
        self.model.add_mission_item(0, 16, 47.397742, 8.545594, 30.0)
        self.model.mission.ready = True
        self.model.mission_status = "Download OK (1 Items)"

        data = self.gui.get_mission_view_data()

        self.assertEqual(data["mission_text"], "Mission: 1 Waypoints")
        self.assertEqual(data["waypoints"], ["00: CMD 16 (47.39774, 8.54559, 30.0)"])
        self.assertEqual(data["status_text"], "Status: Download OK (1 Items)")

    def test_update_mission_tab_enables_buttons_when_idle(self, _print):
        window = MagicMock()
        self.gui.main_window = window
        self.model.mission_ms = MagicMock()

        self.gui.update_mission_tab()

        window.mission_tab.set_enabled.assert_called_once_with(upload=True, download=True, stop=False, start=False)
        window.mission_tab.show_mission.assert_called_once()

    def test_update_mission_tab_start_needs_mission(self, _print):
        window = MagicMock()
        self.gui.main_window = window
        self.model.mission_ms = MagicMock()
        self.model.mission.ready = True

        self.gui.update_mission_tab()

        window.mission_tab.set_enabled.assert_called_once_with(upload=True, download=True, stop=False, start=True)

    def test_update_mission_tab_stop_only_during_transfer(self, _print):
        window = MagicMock()
        self.gui.main_window = window
        self.model.mission_ms = MagicMock()

        for sub in ("UPLOAD", "DOWNLOAD"):
            with self.subTest(sub=sub):
                window.reset_mock()
                self.model.hfsm_sub = sub
                self.gui.update_mission_tab()
                window.mission_tab.set_enabled.assert_called_once_with(
                    upload=False, download=False, stop=True, start=False)

    def test_update_mission_tab_disables_buttons(self, _print):
        window = MagicMock()
        self.gui.main_window = window

        for main, sub, ms in (("READY", "IDLE", MagicMock()),
                              ("MISSION", "IDLE", None)):
            with self.subTest(main=main, sub=sub, ms=ms):
                window.reset_mock()
                self.model.hfsm_main, self.model.hfsm_sub, self.model.mission_ms = main, sub, ms
                self.gui.update_mission_tab()
                window.mission_tab.set_enabled.assert_called_once_with(
                    upload=False, download=False, stop=False, start=False)


@patch("builtins.print")
class TestControllerGUIControllerModel(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.hfsm_main = "READY"
        self.model.vehicle_configs = [PX4InstanceConfig("/opt/px4", "gz_rc_cessna", 1, verbose=False)]
        self.gui = GUIController(self.model, None, None, self.model.queue_registry)

    def test_choices_and_selected(self, _print):
        self.assertEqual(self.gui.get_model_choices(), ["gz_rc_cessna", "gz_fsl_rocket_vtol"])
        self.assertEqual(self.gui.get_selected_model(), "gz_rc_cessna")

    def test_change_updates_config_and_triggers_reset(self, _print):
        self.assertTrue(self.gui.request_model_change("gz_fsl_rocket_vtol"))

        cfg = self.model.vehicle_configs[0]
        self.assertEqual((cfg.model_name, cfg.px4_dir, cfg.instance_id),
                         ("gz_fsl_rocket_vtol", "/opt/px4", 1))
        self.assertEqual(list(self.model.hfsm_events), ["RESET"])

    def test_change_allowed_in_startup_ready_mission(self, _print):
        for state in ("STARTUP", "READY", "MISSION"):
            with self.subTest(state=state):
                self.model.vehicle_configs[0].model_name = "gz_rc_cessna"
                self.model.hfsm_events.clear()
                self.model.hfsm_main = state
                self.assertTrue(self.gui.request_model_change("gz_fsl_rocket_vtol"))

    def test_change_blocked_in_flight_and_reset(self, _print):
        for state in ("AIRBORNE", "RESET"):
            with self.subTest(state=state):
                self.model.hfsm_main = state
                self.assertFalse(self.gui.request_model_change("gz_fsl_rocket_vtol"))
                self.assertEqual(self.gui.get_selected_model(), "gz_rc_cessna")
                self.assertEqual(len(self.model.hfsm_events), 0)

    def test_same_or_unknown_model_ignored(self, _print):
        self.assertFalse(self.gui.request_model_change("gz_rc_cessna"))
        self.assertFalse(self.gui.request_model_change("gz_x500"))
        self.assertEqual(len(self.model.hfsm_events), 0)

    def test_update_model_selector(self, _print):
        window = MagicMock()
        self.gui.main_window = window

        self.gui.update_model_selector()
        window.home_tab.set_model.assert_called_with("gz_rc_cessna", enabled=True)

        self.model.hfsm_main = "AIRBORNE"
        self.gui.update_model_selector()
        window.home_tab.set_model.assert_called_with("gz_rc_cessna", enabled=False)


if __name__ == "__main__":
    unittest.main()
