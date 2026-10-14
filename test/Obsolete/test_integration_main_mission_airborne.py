# === PFAD-B FULL FILE: test_integration_main_mission_airborne.py ===

import unittest

from QGCR.test.unittest.dummy_model import DummyModel
from QGCR.states.main.main_hfsm import MainHFSM
from QGCR.states.main_state import MainState


# ------------------------------------------------------------
# Dummy HFSMs für Integrationstest
# ------------------------------------------------------------

class DummyReadyHFSM:
    def __init__(self, model):
        self.model = model
        self.events = []

    def on_update(self):
        return MainState.READY

    def handle_event(self, event):
        self.events.append(event)


class DummyMissionHFSM:
    def __init__(self, model):
        self.model = model
        self.events = []

    def on_update(self):
        return MainState.MISSION

    def handle_event(self, event):
        self.events.append(event)


class DummyAirborneHFSM:
    def __init__(self, model):
        self.model = model
        self.events = []
        self.counter = 0

    def on_update(self):
        # Simuliere AIRBORNE → AIRBORNE (bleibt im Flug)
        return MainState.AIRBORNE

    def handle_event(self, event):
        self.events.append(event)


class DummyLostHFSM:
    def __init__(self, model):
        self.model = model
        self.events = []

    def on_update(self):
        return MainState.LOST

    def handle_event(self, event):
        self.events.append(event)


# ------------------------------------------------------------
# Integrationstest
# ------------------------------------------------------------

class TestIntegrationMainMissionAirborne(unittest.TestCase):

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

    # ------------------------------------------------------------
    # READY → MISSION
    # ------------------------------------------------------------
    def test_ready_to_mission_transition(self):
        # Simuliere, dass READY-HFSM MISSION zurückgibt
        self.hfsm.active_hfsm = DummyMissionHFSM(self.model)
        self.hfsm.entered = False

        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.MISSION)
        self.assertIsInstance(self.hfsm.active_hfsm, DummyMissionHFSM)

    # ------------------------------------------------------------
    # MISSION → AIRBORNE
    # ------------------------------------------------------------
    def test_mission_to_airborne_transition(self):
        self.hfsm.active_hfsm = DummyAirborneHFSM(self.model)
        self.hfsm.entered = False

        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.AIRBORNE)
        self.assertIsInstance(self.hfsm.active_hfsm, DummyAirborneHFSM)

    # ------------------------------------------------------------
    # AIRBORNE bleibt AIRBORNE
    # ------------------------------------------------------------
    def test_airborne_stays_airborne(self):
        self.hfsm.active_hfsm = DummyAirborneHFSM(self.model)
        self.hfsm.entered = False

        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.AIRBORNE)

        # Zweiter Tick
        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.AIRBORNE)

    # ------------------------------------------------------------
    # Event-Delegation über alle States
    # ------------------------------------------------------------
    def test_event_delegation(self):
        self.hfsm.on_update()  # initialisieren

        self.hfsm.handle_event("EVT_TEST")
        self.assertIn("EVT_TEST", self.hfsm.active_hfsm.events)

    # ------------------------------------------------------------
    # READY → MISSION → AIRBORNE (komplette Kette)
    # ------------------------------------------------------------
    def test_full_chain_ready_mission_airborne(self):
        # READY → MISSION
        self.hfsm.active_hfsm = DummyMissionHFSM(self.model)
        self.hfsm.entered = False
        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.MISSION)

        # MISSION → AIRBORNE
        self.hfsm.active_hfsm = DummyAirborneHFSM(self.model)
        self.hfsm.entered = False
        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.AIRBORNE)

        # AIRBORNE bleibt AIRBORNE
        state = self.hfsm.on_update()
        self.assertEqual(state, MainState.AIRBORNE)


if __name__ == "__main__":
    unittest.main()
