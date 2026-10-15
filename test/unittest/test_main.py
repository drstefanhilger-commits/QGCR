# === PFAD-B FULL FILE: QGCR/test/unittest/test_main.py ===

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from QGCR.main import Application, parse_args
from QGCR.model.model import MissionData
from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.test.unittest.dummy_model import DummyModel


class TestMainConnectLoop(unittest.TestCase):
    """
    Application._connect_loop() legt nach dem ersten Heartbeat den MissionMicroService an,
    ohne model.mission (MissionData) zu überschreiben.
    """

    def setUp(self):
        self.model = DummyModel()
        self.model.px4_connected = True

        master = MagicMock()
        master.target_system = 1
        master.target_component = 1

        self.connection = MagicMock()
        self.connection.master = master

        self.app = SimpleNamespace(model=self.model, connection=self.connection, _stop=False)

    @patch("builtins.print")
    def run_connect_loop(self, _print):
        Application._connect_loop(self.app)

    def test_mission_data_is_kept(self):
        mission_data = self.model.mission
        self.run_connect_loop()

        self.assertIs(self.model.mission, mission_data)
        self.assertIsInstance(self.model.mission, MissionData)

    def test_mission_service_in_mission_ms(self):
        self.run_connect_loop()

        self.connection.connect.assert_called_once()
        self.assertIsInstance(self.model.mission_ms, MissionMicroService)
        self.assertIs(self.model.services.mission, self.model.mission_ms)
        self.assertEqual(self.model.mission_ms.target_system, 1)
        self.assertEqual(self.model.mission_ms.target_component, 1)

    def test_connect_loop_ends_on_stop_without_px4(self):
        import threading
        self.model.px4_connected = False          # PX4 meldet sich nie
        self.app._stop = False

        t = threading.Thread(target=self.run_connect_loop, daemon=True)
        t.start()
        self.app._stop = True
        t.join(2.0)

        self.assertFalse(t.is_alive())
        self.assertNotIsInstance(self.model.mission_ms, MissionMicroService)

    def test_mission_view_data_still_works(self):
        from QGCR.controller.gui_controller import GUIController

        self.run_connect_loop()
        gui = GUIController(self.model, None, None, self.model.queue_registry)

        self.assertEqual(gui.get_mission_view_data()["mission_text"], "Mission: -")


class TestMainParseArgs(unittest.TestCase):

    def test_default_model(self):
        self.assertEqual(parse_args([]).model, "gz_rc_cessna")

    def test_vtol_model(self):
        self.assertEqual(parse_args(["--model", "gz_fsl_rocket_vtol"]).model, "gz_fsl_rocket_vtol")

    @patch("sys.stderr")
    def test_unknown_model_rejected(self, _stderr):
        with self.assertRaises(SystemExit):
            parse_args(["--model", "gz_x500"])


class TestMainApplicationModel(unittest.TestCase):

    @patch("builtins.print")
    @patch("QGCR.main.threading.Thread")
    @patch("QGCR.main.StartupCleanup")
    def test_model_name_goes_into_vehicle_config(self, cleanup, _thread, _print):
        app = Application(model_name="gz_fsl_rocket_vtol")
        try:
            self.assertEqual([c.model_name for c in app.model.vehicle_configs], ["gz_fsl_rocket_vtol"])
        finally:
            app.root.destroy()

    @patch("QGCR.main.StartupCleanup")
    def test_unknown_model_raises_before_cleanup(self, cleanup):
        with self.assertRaises(ValueError):
            Application(model_name="gz_x500")
        cleanup.run_full_cleanup.assert_not_called()


class TestMainApplicationInit(unittest.TestCase):
    """
    Application() ohne Cleanup und ohne Threads aufbauen.
    """

    @patch("builtins.print")
    @patch("QGCR.main.threading.Thread")
    @patch("QGCR.main.StartupCleanup")
    def setUp(self, cleanup, thread, _print):
        self.app = Application()
        self.app.root.withdraw()
        self.cleanup = cleanup

    def tearDown(self):
        self.app.root.destroy()

    def test_shutdown_stops_px4_and_closes(self):
        starter = MagicMock()
        self.app.model.startup_controller = starter
        self.app.connection = MagicMock()

        with patch.object(self.app.root, "destroy") as destroy:
            self.app.shutdown()
            self.app.shutdown()                  # zweiter Aufruf ohne Wirkung

        self.assertTrue(self.app._stop)
        self.app.connection.close.assert_called_once()
        starter.stop_all.assert_called_once()
        destroy.assert_called_once()

    def test_window_close_calls_shutdown(self):
        """Klick auf X (WM_DELETE_WINDOW) fährt QGCR herunter."""
        starter = MagicMock()
        self.app.model.startup_controller = starter

        with patch.object(self.app.root, "destroy") as destroy:
            self.app.root.tk.call(self.app.root.protocol("WM_DELETE_WINDOW"))

        self.assertTrue(self.app._shut_down)
        starter.stop_all.assert_called_once()
        destroy.assert_called_once()

    def test_update_loop_processes_messages_before_tick(self):
        calls = []
        self.app.connection = MagicMock()
        self.app.connection.process_pending.side_effect = lambda: calls.append("pending")
        self.app.model.check_timeout = lambda: calls.append("timeout")
        self.app.ms_controller = MagicMock()
        self.app.main_controller = MagicMock()
        self.app.main_controller.on_update.side_effect = lambda: calls.append("hfsm")

        def stop_after_one(_):
            self.app._stop = True

        with patch("QGCR.main.time.sleep", side_effect=stop_after_one):
            self.app._stop = False
            self.app._update_loop()

        self.assertEqual(calls, ["pending", "timeout", "hfsm"])

    def test_update_loop_requests_gazebo_markers(self):
        self.app.connection = MagicMock()
        self.app.ms_controller = MagicMock()
        self.app.main_controller = MagicMock()
        self.app.gz_markers = MagicMock()
        m = self.app.model

        def one_tick():
            with patch("QGCR.main.time.sleep", side_effect=lambda _: setattr(self.app, "_stop", True)):
                self.app._stop = False
                self.app._update_loop()

        m.hfsm_main = "STARTUP"
        one_tick()
        self.app.gz_markers.invalidate.assert_called_once()
        self.app.gz_markers.request.assert_not_called()

        m.hfsm_main = "READY"
        m.update_home_position(47.0, 8.0, 400.0)
        one_tick()
        self.app.gz_markers.request.assert_called_once_with((47.0, 8.0), None, path=None, wait=None)

    def test_shutdown_stops_gazebo_markers(self):
        self.app.gz_markers = MagicMock()
        with patch.object(self.app.root, "destroy"):
            self.app.shutdown()
        self.app.gz_markers.stop.assert_called_once()

    def test_cleanup_runs_first(self):
        self.cleanup.run_full_cleanup.assert_called_once()

    def test_microservices_exist_once(self):
        m = self.app.model

        self.assertFalse(hasattr(m, "upload"))
        self.assertFalse(hasattr(m, "home"))
        self.assertIs(m.services.takeoff, m.takeoff)
        self.assertIs(m.services.upload, m.upload_ms)
        self.assertIs(m.services.home, m.home_ms)
        self.assertIs(m.services.reset, m.reset)

    def test_microservices_use_application_connection(self):
        m = self.app.model
        for svc in (m.takeoff, m.upload_ms, m.home_ms):
            self.assertIs(svc.connection, self.app.connection)

    @patch("builtins.print")
    def test_dispatcher_reaches_ticked_takeoff_service(self, _print):
        takeoff = self.app.model.takeoff
        takeoff.on_message = MagicMock()

        msg = MagicMock()
        msg.get_type.return_value = "COMMAND_ACK"
        self.app.dispatcher.dispatch(msg)

        takeoff.on_message.assert_called_once_with("COMMAND_ACK", msg)

    def test_status_messages_reach_status_bar_and_log(self):
        from QGCR.test.unittest.fake_mavlink import make_msg

        self.app.model.on_command_ack(make_msg("COMMAND_ACK", command=400, result=0))
        self.app.model.update_home_position(47.3977418, 8.5455939, 488.0)

        self.app.gui_controller.gui_tick()

        window = self.app.window
        self.assertEqual(window.status_bar.message_var.get(), "Home set: 47.39774, 8.54559, 488.0 m")
        log = window.log_tab.qgcr_text.get("1.0", "end")
        self.assertIn("[STATUS] ACK: 400 → 0", log)
        self.assertIn("[STATUS] Home set: 47.39774, 8.54559, 488.0 m", log)

    @patch("builtins.print")
    @patch("QGCR.states.startup.startup_hfsm.PX4SwarmStarter")
    def test_mission_tab_switches_ready_mission_ready(self, _starter, _print):
        from QGCR.states.main_state import MainState

        ctrl = self.app.main_controller
        model = self.app.model
        model.px4_connected = True
        model.px4_heartbeat_count = 1

        ctrl.on_update()                       # STARTUP → READY
        self.assertEqual(ctrl.active_state, MainState.READY)
        ctrl.on_update()                       # READY: enter

        self.select_tab("Mission")
        ctrl.on_update()
        self.assertEqual(ctrl.active_state, MainState.MISSION)
        ctrl.on_update()                       # MISSION: enter

        self.select_tab("Log")
        ctrl.on_update()
        self.assertEqual(ctrl.active_state, MainState.MISSION)

        self.select_tab("Home")
        ctrl.on_update()
        self.assertEqual(ctrl.active_state, MainState.READY)

    def select_tab(self, text):
        nb = self.app.window.notebook
        for tab_id in nb.tabs():
            if nb.tab(tab_id, "text") == text:
                nb.select(tab_id)
        self.app.root.update()


if __name__ == "__main__":
    unittest.main()
