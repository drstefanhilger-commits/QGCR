# === PFAD-B FULL FILE: test_main_hfsm.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.main.main_hfsm import MainHFSM
from QGCR.states.main_state import MainState


# ------------------------------------------------------------
# Dummy HFSMs für isolierte Tests
# ------------------------------------------------------------

class DummyHFSM_Base:
    def __init__(self, model):
        self.model = model
        self.events = []

    def on_update(self):
        return MainState.READY

    def handle_event(self, event):
        self.events.append(event)


class DummyReadyHFSM(DummyHFSM_Base):
    def on_update(self):
        return MainState.READY


class DummyMissionHFSM(DummyHFSM_Base):
    def on_update(self):
        return MainState.MISSION


class DummyAirborneHFSM(DummyHFSM_Base):
    def on_update(self):
        return MainState.AIRBORNE


class DummyLostHFSM(DummyHFSM_Base):
    def on_update(self):
        return MainState.LOST


# ------------------------------------------------------------
# Testklasse
# ------------------------------------------------------------

class TestMainHFSM(unittest.TestCase):

    def setUp(self):
        self.model = DummyModel()

        # Wir ersetzen ALLE echten HFSMs durch Dummy-Versionen
        self.state_map = {
            MainState.READY: DummyReadyHFSM,
            MainState.MISSION: DummyMissionHFSM,
            MainState.AIRBORNE: DummyAirborneHFSM,
            MainState.LOST: DummyLostHFSM,
        }

        self.hfsm = MainHFSM(
            model=self.model,
            state_map=self.state_map,
            initial_state=MainState.READY
        )

    def test_initial_state_is_ready(self):
        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.READY)
        self.assertIsInstance(self.hfsm.active_hfsm, DummyReadyHFSM)

    def test_transition_to_mission(self):
        self.hfsm.active_hfsm = DummyMissionHFSM(self.model)
        self.hfsm.entered = False

        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.MISSION)
        self.assertIsInstance(self.hfsm.active_hfsm, DummyMissionHFSM)

    def test_transition_to_airborne(self):
        self.hfsm.active_hfsm = DummyAirborneHFSM(self.model)
        self.hfsm.entered = False

        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.AIRBORNE)
        self.assertIsInstance(self.hfsm.active_hfsm, DummyAirborneHFSM)

    def test_transition_to_lost(self):
        self.hfsm.active_hfsm = DummyLostHFSM(self.model)
        self.hfsm.entered = False

        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.LOST)
        self.assertIsInstance(self.hfsm.active_hfsm, DummyLostHFSM)

    def test_event_is_forwarded(self):
        self.hfsm.on_update()  # initialisieren
        self.hfsm.handle_event("TEST_EVENT")

        self.assertIn("TEST_EVENT", self.hfsm.active_hfsm.events)


if __name__ == "__main__":
    unittest.main()
