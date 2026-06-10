# === PFAD-B FULL FILE: QGCR/test/test_harness_param_sync.py ===

import unittest
from types import SimpleNamespace

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher
from QGCR.communication.microservices.parameter_sync_microservice import ParameterSyncMicroService


# ------------------------------------------------------------
# Fake Model
# ------------------------------------------------------------
class FakeModel:
    def __init__(self):
        self.services = SimpleNamespace()
        self.params = {}


# ------------------------------------------------------------
# Fake MAVLink Master
# ------------------------------------------------------------
class FakeMav:
    def __init__(self, parent):
        self.parent = parent

    def param_request_list_send(self, target_system, target_component):
        self.parent.sent.append(("PARAM_REQUEST_LIST", (target_system, target_component)))


class FakeMaster:
    def __init__(self):
        self.sent = []
        self.mav = FakeMav(self)

    def recv_match(self, *args, **kwargs):
        return None


# ------------------------------------------------------------
# Fake Connection
# ------------------------------------------------------------
class FakeConnection(Connection):
    def connect(self):
        self.master = FakeMaster()
        self._worker = None
        self._gcs_hb_thread = None


# ------------------------------------------------------------
# Fake PX4 PARAM_VALUE
# ------------------------------------------------------------
def make_param_value(name, value, index, count):
    msg = SimpleNamespace()
    msg.get_type = lambda: "PARAM_VALUE"
    msg.param_id = name
    msg.param_value = float(value)
    msg.param_index = index
    msg.param_count = count
    return msg


# ------------------------------------------------------------
# Minimal FSM
# ------------------------------------------------------------
class FakeParamSyncFSM:
    def __init__(self, service):
        self.service = service

    def start(self):
        self.service.start()

    def tick(self):
        self.service.tick()


# ------------------------------------------------------------
# HARNESS TEST
# ------------------------------------------------------------
class TestHarnessParamSync(unittest.TestCase):

    def test_param_sync_end_to_end(self):
        model = FakeModel()
        dispatcher = Dispatcher(model)
        conn = FakeConnection(model, dispatcher)
        conn.connect()

        service = ParameterSyncMicroService(
            connection=conn,
            model=model,
            timeout=0.3,
        )
        model.services.param_sync = service

        fsm = FakeParamSyncFSM(service)
        fsm.start()

        # Tick 1: send PARAM_REQUEST_LIST
        fsm.tick()
        self.assertEqual(conn.master.sent[0][0], "PARAM_REQUEST_LIST")

        # PX4 sends 3 PARAM_VALUE messages
        service.on_param_value(make_param_value("SYS_ID", 1.0, 0, 3))
        service.on_param_value(make_param_value("MPC_XY_VEL_MAX", 5.0, 1, 3))
        service.on_param_value(make_param_value("MPC_Z_VEL_MAX_DN", 1.5, 2, 3))

        # Tick 2: WAIT_VALUES -> DONE
        fsm.tick()
        self.assertTrue(service.done)
        self.assertIsNone(service.error)

        # Check that all params are stored
        self.assertIn("SYS_ID", model.params)
        self.assertIn("MPC_XY_VEL_MAX", model.params)
        self.assertIn("MPC_Z_VEL_MAX_DN", model.params)

        self.assertEqual(model.params["SYS_ID"][0], 1.0)
        self.assertEqual(model.params["MPC_XY_VEL_MAX"][0], 5.0)
        self.assertEqual(model.params["MPC_Z_VEL_MAX_DN"][0], 1.5)


if __name__ == "__main__":
    unittest.main()
