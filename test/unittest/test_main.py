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


if __name__ == "__main__":
    unittest.main()
