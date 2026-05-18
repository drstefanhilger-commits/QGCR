# === PFAD-B FULL FILE: QGCR/harness/test_px4_ready_takeoff_airborne.py ===

import unittest
from QGCR.harness.px4_sitl_harness import start_px4_harness
from QGCR.states.main.main_hfsm import MainHFSM
from QGCR.states.main.main_state import MainState


class TestPX4ReadyTakeoffAirborne(unittest.TestCase):
    """
    Integrationstest gegen echten PX4-SITL.
    Läuft NICHT automatisch mit normalen Unittests.
    """

    @classmethod
    def setUpClass(cls):
        cls.harness = start_px4_harness()
        cls.model = cls.harness.model

    @classmethod
    def tearDownClass(cls):
        cls.harness.shutdown()

    def setUp(self):
        self.hfsm = MainHFSM(self.model)
        self.hfsm.on_update()  # READYHFSM erzeugen

    def test_takeoff_to_airborne_px4(self):
        # TAKEOFF Event
        self.hfsm.handle_event("TAKEOFF")
        self.hfsm.on_update()

        # Warten bis PX4 Höhe erreicht
        for _ in range(300):
            self.hfsm.on_update()
            if self.hfsm.state_enum == MainState.AIRBORNE:
                break

        self.assertEqual(self.hfsm.state_enum, MainState.AIRBORNE)


if __name__ == "__main__":
    unittest.main()
