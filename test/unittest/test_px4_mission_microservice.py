# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_mission_microservice.py ===

import time
import unittest
from unittest.mock import patch

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl
from QGCR.test.utils.mission_item_builder import make_waypoint


@requires_sitl
class TestPX4MissionMicroService(unittest.TestCase):
    """
    Mission-Upload/-Download über QGCR-Connection (RX-Thread) + Dispatcher gegen PX4-SITL.
    """

    def setUp(self):
        self.sitl = PX4Sitl()
        self.sitl.start()

        self.model = DummyModel()
        self.conn = Connection(self.model, Dispatcher(self.model))
        self.model.connection = self.conn
        self.conn.connect()

    def tearDown(self):
        self.conn.close()
        self.sitl.stop()

    @patch("builtins.print")
    def test_upload_and_download(self, _print):
        deadline = time.time() + 90
        while time.time() < deadline and not (
            self.model.px4_heartbeat_count > 0 and self.conn.master.target_system
        ):
            time.sleep(0.2)
        self.assertGreater(self.model.px4_heartbeat_count, 0, "Kein PX4 HEARTBEAT")

        master = self.conn.master
        self.model.mission_ms = MissionMicroService(
            master, master.target_system, master.target_component, timeout=5.0
        )

        mission = [
            make_waypoint(0, 47.397742, 8.545594, 30),
            make_waypoint(1, 47.398500, 8.546500, 40),
            make_waypoint(2, 47.399000, 8.545000, 50),
            make_waypoint(3, 47.398000, 8.544000, 40),
        ]

        self.assertTrue(self.model.mission_ms.upload(mission), "Upload nicht akzeptiert")

        downloaded = self.model.mission_ms.download()

        self.assertEqual([m.seq for m in downloaded], [0, 1, 2, 3])
        for sent, got in zip(mission, downloaded):
            self.assertEqual(got.command, sent.command)
            self.assertEqual(got.x, sent.x)
            self.assertEqual(got.y, sent.y)


if __name__ == "__main__":
    unittest.main()
