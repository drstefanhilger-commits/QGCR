# === PFAD-B FULL FILE: QGCR/test/unittest/test_controller_microservice_controller.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.controller.microservice_controller import MicroServiceController
from QGCR.microservices.takeoff_ms import TakeoffMicroService
from QGCR.microservices.upload_ms import UploadMicroService
from QGCR.microservices.home_ms import HomeMicroService
from QGCR.microservices.reset_microservice import ResetMicroService
from QGCR.test.unittest.dummy_model import DummyModel


class TestControllerMicroServiceController(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.model.connection = MagicMock()
        self.ctrl = MicroServiceController(self.model)

    def test_creates_services_with_aliases(self):
        m = self.model
        self.assertIsInstance(m.takeoff, TakeoffMicroService)
        self.assertIsInstance(m.upload_ms, UploadMicroService)
        self.assertIsInstance(m.home_ms, HomeMicroService)
        self.assertIsInstance(m.reset, ResetMicroService)

        self.assertIs(m.services.takeoff, m.takeoff)
        self.assertIs(m.services.upload, m.upload_ms)
        self.assertIs(m.services.home, m.home_ms)
        self.assertIs(m.services.reset, m.reset)

    def test_tick_ticks_all_services(self):
        for name in ("upload_ms", "home_ms", "takeoff", "reset"):
            setattr(self.model, name, MagicMock())
        self.model.services.param_sync = MagicMock()

        self.ctrl.tick()

        for svc in (self.model.services.param_sync, self.model.upload_ms,
                    self.model.home_ms, self.model.takeoff, self.model.reset):
            svc.tick.assert_called_once()

    def test_tick_error_is_logged_and_others_continue(self):
        self.model.upload_ms = MagicMock()
        self.model.upload_ms.tick.side_effect = RuntimeError("boom")
        self.model.takeoff = MagicMock()

        self.ctrl.tick()

        self.model.takeoff.tick.assert_called_once()
        self.assertIn("[QGCR] [MicroServiceController] ERROR in upload_ms.tick(): boom",
                      self.model.qgcr_logs())


if __name__ == "__main__":
    unittest.main()
