# === PFAD-B FULL FILE: QGCR/test/test_harness_startup_full.py ===

import unittest
from types import SimpleNamespace
from collections import deque

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.main_state import MainState

from QGCR.communication.connection import Connection
from QGCR.communication.dispatcher import Dispatcher


class FakeModel:
    def __init__(self):
        self.services = SimpleNamespace()

        self.px4_connected = False
        self.px4_heartbeat_count = 0

        self.mission = SimpleNamespace()
        self.mission.items = []
        self.mission.count = 0
        self.mission.ready = False

        self.gui_events = deque()

        self.queue_registry = SimpleNamespace()
        self.queue_registry.require = lambda name: SimpleNamespace(push=lambda x: None)

    def clear_mission(self):
        self.mission.items = []
        self.mission.count = 0
        self.mission.ready = False

    def add_mission_item(self, seq, cmd, x, y, z):
        self.mission.items.append((seq, cmd, x, y, z))
        self.mission.count = len(self.mission.items)


class FakeParamSyncMS:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True


class FakeMissionMS:
    def __init__(self, msgs):
        self.msgs = msgs

    def download(self):
        return self.msgs


class FakeConnection(Connection):
    def connect(self):
        self.master = None
        self._worker = None
        self._gcs_hb_thread = None


def make_mission_item(seq, cmd=16, x=47.0, y=8.0, z=10.0):
    msg = SimpleNamespace()
    msg.seq = seq
    msg.command = cmd
    msg.x = int(x * 1e7)
    msg.y = int(y * 1e7)
    msg.z = int(z * 1000)
    return msg


class TestStartupFull(unittest.TestCase):

    def test_full_startup_pipeline(self):
        model = FakeModel()
        dispatcher = Dispatcher(model)
        conn = FakeConnection(model, dispatcher)
        conn.connect()

        model.services.param_sync = FakeParamSyncMS()
        model.services.mission = FakeMissionMS([
            make_mission_item(0),
            make_mission_item(1),
        ])

        fsm = StartupHFSM(model)

        # 1: Heartbeat-FSM aktiv
        fsm.on_update()
        self.assertEqual(fsm.active_substate.name, "STARTUP_HEARTBEAT")

        # Heartbeat kommt
        model.px4_connected = True
        model.px4_heartbeat_count = 1

        # 2: Wechsel zu STARTUP_PARAMS (ParamSync-FSM nur instanziiert)
        fsm.on_update()
        self.assertEqual(fsm.active_substate.name, "STARTUP_PARAMS")

        # 3: ParamSync-FSM läuft → weiter zu STARTUP_HOME
        fsm.on_update()
        self.assertEqual(fsm.active_substate.name, "STARTUP_HOME")
        self.assertTrue(model.services.param_sync.started)

        # 4: Home-FSM → STARTUP_MISSION
        fsm.on_update()
        self.assertEqual(fsm.active_substate.name, "STARTUP_MISSION")

        # 5: Mission-FSM → STARTUP_OK
        fsm.on_update()
        self.assertEqual(fsm.active_substate.name, "STARTUP_OK")
        self.assertEqual(model.mission.count, 2)
        self.assertTrue(model.mission.ready)

        # 6: HFSM → READY
        fsm.on_update()
        self.assertEqual(fsm.state_enum, MainState.READY)


if __name__ == "__main__":
    unittest.main()
