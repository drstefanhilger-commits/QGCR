# === PFAD-B FULL FILE: QGCR/test/unittest/test_px4_sitl_harness.py ===

import time
import unittest

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.test.unittest.fake_mavlink import UpdatePump
from QGCR.test.unittest.sitl_helper import PX4Sitl, requires_sitl


@requires_sitl
class TestPX4SITLHarness(unittest.TestCase):
    """
    End-to-End: PX4-SITL → QGCR-Connection → Model.
    """

    def setUp(self):
        self.sitl = PX4Sitl()
        self.sitl.start()

        self.model = DummyModel()
        self.dispatcher = Dispatcher(self.model)
        self.connection = Connection(self.model, self.dispatcher)
        self.connection.connect()
        self.pump = UpdatePump(self.connection).start()

    def tearDown(self):
        self.pump.stop()
        self.connection.close()
        self.sitl.stop()

    def test_px4_heartbeat_pipeline(self):
        deadline = time.time() + 90.0
        while time.time() < deadline and self.model.px4_heartbeat_count < 3:
            time.sleep(0.2)

        self.assertGreaterEqual(
            self.model.px4_heartbeat_count,
            3,
            "PX4-SITL hat in der erwarteten Zeit keine Heartbeats bis ins Model geliefert",
        )
        self.assertTrue(self.model.px4_connected)
        self.assertNotEqual(self.model.px4_mode, "-")


if __name__ == "__main__":
    unittest.main()
