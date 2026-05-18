from QGCR.states.main_state import MainState

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM
from QGCR.states.mission.mission_hfsm import MissionHFSM


class MainStateMachine:
    """
    High-Level Router für die vier Superstates:
    - STARTUP
    - READY
    - AIRBORNE
    - MISSION

    Diese Klasse ruft ausschließlich on_update() der aktiven HFSM auf.
    Sie ruft niemals on_enter(), on_during() oder on_exit() direkt auf.
    """

    def __init__(self, model):
        self.model = model

        # HFSM-Instanzen
        self.startup_fsm = StartupHFSM(model)
        self.ready_fsm = ReadyHFSM(model)
        self.airborne_fsm = AirborneHFSM(model)
        self.mission_fsm = MissionHFSM(model)

        # Startzustand
        self.current_state = MainState.STARTUP

    # ------------------------------------------------------------
    # Update Loop
    # ------------------------------------------------------------
    def update(self):
        """
        Führt genau EINEN Tick der aktiven HFSM aus.
        Ruft IMMER nur on_update() auf.
        """

        if self.current_state == MainState.STARTUP:
            next_state = self.startup_fsm.on_update()

        elif self.current_state == MainState.READY:
            next_state = self.ready_fsm.on_update()

        elif self.current_state == MainState.AIRBORNE:
            next_state = self.airborne_fsm.on_update()

        elif self.current_state == MainState.MISSION:
            next_state = self.mission_fsm.on_update()

        else:
            next_state = MainState.STARTUP

        # State-Wechsel
        if next_state != self.current_state:
            self._transition(next_state)

    # ------------------------------------------------------------
    # Transitionen
    # ------------------------------------------------------------
    def _transition(self, new_state):
        """
        Führt den State-Wechsel durch.
        Setzt _entered=False für die neue HFSM,
        damit BaseFSM.on_update() korrekt enter/during/exit ausführt.
        """

        self.current_state = new_state

        if new_state == MainState.STARTUP:
            self.startup_fsm._entered = False

        elif new_state == MainState.READY:
            self.ready_fsm._entered = False

        elif new_state == MainState.AIRBORNE:
            self.airborne_fsm._entered = False

        elif new_state == MainState.MISSION:
            self.mission_fsm._entered = False
