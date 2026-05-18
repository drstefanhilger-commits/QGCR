from QGCR.states.main_state_machine import MainStateMachine
from QGCR.states.main_state import MainState


class StateMachineController:
    """
    Oberste Kontrollinstanz für die gesamte System-FSM.
    - Hält eine Instanz von MainStateMachine
    - Führt step() aus
    - Gibt ausschließlich den aktuellen MainState zurück
    - GUI bleibt vollständig state-agnostisch
    """

    def __init__(self, model):
        self.model = model
        self.system_sm = MainStateMachine(model)

    def step(self) -> MainState:
        """
        Führt genau einen Tick der MainStateMachine aus.
        Gibt den aktuellen MainState zurück.
        """
        self.system_sm.update()
        return self.system_sm.current_state
