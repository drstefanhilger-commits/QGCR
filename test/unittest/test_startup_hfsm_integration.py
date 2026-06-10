# === PFAD-B FULL FILE: test_startup_hfsm_integration.py ===

import unittest

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.main_state import MainState
from QGCR.states.startup_substate import SubState

from QGCR.states.startup.subfsms.startup_heartbeat_fsm import StartupHeartbeatFSM
from QGCR.states.startup.subfsms.startup_param_sync_fsm import StartupParamSyncFSM
from QGCR.states.startup.subfsms.startup_home_fsm import StartupHomeFSM
from QGCR.states.startup.subfsms.startup_ok_fsm import StartupOKFSM

from QGCR.events.event import (
    px4_heartbeat,
    px4_params_received,
    px4_params_synced,
    px4_home_set,
)

from QGCR.test.dummy_model import DummyModel


class TestStartupHFSMIntegration(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()

        # WICHTIG: state_map MUSS HIER stehen
        self.state_map = {
            SubState.STARTUP_HEARTBEAT: StartupHeartbeatFSM,
            SubState.STARTUP_PARAMS: StartupParamSyncFSM,
            SubState.STARTUP_HOME: StartupHomeFSM,
            SubState.STARTUP_OK: StartupOKFSM,
        }

        self.fsm = StartupHFSM(self.model, self.state_map)

    def test_full_startup_sequence(self):
        """
        Integrationstest:
        - Heartbeat → PARAMS
        - Params Received → bleibt PARAMS
        - Params Synced → HOME
        - Home Set → READY
        """

        # Tick 1: HFSM enters STARTUP, HeartbeatFSM active
        state = self.fsm.on_update()
        self.assertEqual(state, MainState.STARTUP)

        # PX4 Heartbeat kommt rein
        self.model.event_queue.put(px4_heartbeat())

        # Tick 2: HeartbeatFSM → PARAMS
        state = self.fsm.on_update()
        self.assertEqual(state, MainState.STARTUP)

        # PARAMS: zuerst "received"
        self.model.event_queue.put(px4_params_received())

        # Tick 3: bleibt PARAMS
        state = self.fsm.on_update()
        self.assertEqual(state, MainState.STARTUP)

        # PARAMS: jetzt "synced"
        self.model.event_queue.put(px4_params_synced())

        # Tick 4: PARAMS → HOME
        state = self.fsm.on_update()
        self.assertEqual(state, MainState.STARTUP)

        # HOME: Home-Position gesetzt
        self.model.event_queue.put(px4_home_set({"lat": 47.0, "lon": 8.0}))

        # Tick 5: HOME → READY
        state = self.fsm.on_update()
        self.assertEqual(state, MainState.READY)


if __name__ == "__main__":
    unittest.main()
