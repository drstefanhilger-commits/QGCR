# === PFAD-B FULL FILE: test_startup_fsm.py ===

import unittest

from QGCR.test.dummy_model import DummyModel
from QGCR.states.startup_substate import SubState
from QGCR.states.main_state import MainState
from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.events.event import (
    px4_heartbeat,
    px4_params_received,
    px4_params_synced,
    px4_home_set,
)


class TestStartupHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()
        self.fsm = StartupHFSM(self.model, state_map=self.model.startup_state_map)

    def test_sequence(self):
        # Tick 1: HFSM enters STARTUP_HEARTBEAT
        state = self.fsm.on_update()
        self.assertEqual(state, MainState.STARTUP)
        self.assertEqual(self.fsm.controller.current_state, SubState.STARTUP_HEARTBEAT)

        # HEARTBEAT → PARAMS
        self.model.event_queue.put(px4_heartbeat())
        self.fsm.on_update()
        self.assertEqual(self.fsm.controller.current_state, SubState.STARTUP_PARAMS)

        # PARAMS_RECEIVED → bleibt PARAMS
        self.model.event_queue.put(px4_params_received())
        self.fsm.on_update()
        self.assertEqual(self.fsm.controller.current_state, SubState.STARTUP_PARAMS)

        # PARAMS_SYNCED → HOME
        self.model.event_queue.put(px4_params_synced())
        self.fsm.on_update()
        self.assertEqual(self.fsm.controller.current_state, SubState.STARTUP_HOME)

        # HOME_SET → OK → READY
        self.model.event_queue.put(px4_home_set({"lat": 1, "lon": 2}))
        final_state = self.fsm.on_update()
        self.assertEqual(self.fsm.controller.current_state, SubState.STARTUP_OK)
        self.assertEqual(final_state, MainState.READY)


if __name__ == "__main__":
    unittest.main()
