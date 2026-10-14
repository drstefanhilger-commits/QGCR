# === PFAD-B FULL FILE: QGCR/test/unittest/test_main.py ===

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from QGCR.main import Application
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

        self.app = SimpleNamespace(model=self.model, connection=self.connection)

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

    def test_mission_view_data_still_works(self):
        from QGCR.controller.gui_controller import GUIController

        self.run_connect_loop()
        gui = GUIController(self.model, None, None, self.model.queue_registry)

        self.assertEqual(gui.get_mission_view_data()["mission_text"], "Mission: -")


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
