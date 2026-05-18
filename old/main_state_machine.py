# === PFAD-B FULL FILE: QGCR/states/main_state_machine.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_fsm import BaseFSM

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.ready.ready_hfsm import ReadyHFSM


class MainStateMachine:
    """
    High-Level Main State Machine.
    Unterstützte States:
    - STARTUP
    - READY
    - AIRBORNE   (vorerst ignoriert)
    - MISSION    (vorerst ignoriert)
    - LOST       (vorerst ignoriert)
    """

    def __init__(self, model):
        self.model = model
        self.current_state = MainState.STARTUP
        self.active_fsm = None

        # Initialen Zustand setzen
        self._set_state(self.current_state)

    # ------------------------------------------------------------
    # State-Wechsel
    # ------------------------------------------------------------
    def _set_state(self, new_state: MainState):
        """
        Erzeugt die passende HFSM-Instanz für den neuen Zustand.
        """
        self.current_state = new_state

        if new_state == MainState.STARTUP:
            self.active_fsm = StartupHFSM(self.model)

        elif new_state == MainState.READY:
            self.active_fsm = ReadyHFSM(self.model)

        elif new_state == MainState.AIRBORNE:
            # Vorläufig ignoriert → bleibe in READY
            self.current_state = MainState.READY
            self.active_fsm = ReadyHFSM(self.model)

        elif new_state == MainState.MISSION:
            # Vorläufig ignoriert → bleibe in READY
            self.current_state = MainState.READY
            self.active_fsm = ReadyHFSM(self.model)

        elif new_state == MainState.LOST:
            # Vorläufig ignoriert → bleibe in READY
            self.current_state = MainState.READY
            self.active_fsm = ReadyHFSM(self.model)

        else:
            raise ValueError(f"Unbekannter MainState: {new_state}")

    # ------------------------------------------------------------
    # Update
    # ------------------------------------------------------------
    def on_update(self):
        """
        Führt einen Tick der aktiven HFSM aus.
        Wenn die HFSM einen neuen MainState zurückgibt → wechseln.
        """
        next_state = self.active_fsm.on_update()

        if next_state != self.current_state:
            self._set_state(next_state)
