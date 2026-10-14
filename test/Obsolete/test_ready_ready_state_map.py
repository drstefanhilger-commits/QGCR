# === PFAD-B FULL FILE: QGCR/test/unittest/test_ready_ready_state_map.py ===

import unittest
from unittest.mock import MagicMock

from QGCR.states.ready.ready_state_map import READY_STATE_MAP
from QGCR.states.ready.ready_substate import ReadySubState
from QGCR.test.unittest.dummy_model import DummyModel


class TestReadyStateMap(unittest.TestCase):

    def test_every_substate_has_subfsm(self):
        self.assertEqual(set(READY_STATE_MAP), set(ReadySubState))

    def test_subfsm_matches_its_substate(self):
        for substate, fsm_class in READY_STATE_MAP.items():
            with self.subTest(substate=substate):
                model = DummyModel()
                model.services.takeoff = MagicMock()
                fsm = fsm_class(model)
                self.assertEqual(fsm.state_enum, substate)


if __name__ == "__main__":
    unittest.main()
