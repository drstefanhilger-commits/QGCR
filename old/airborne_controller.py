# === PFAD-B FULL FILE: QGCR/states/airborne/airborne_controller.py ===

from QGCR.states.airborne.airborne_substate import AirborneSubState


class AirborneController:
    """
    Controller für die AIRBORNE-SubFSMs.
    Verwaltet ausschließlich:
        * AIRBORNE_HOLD
        * AIRBORNE_MISSION
        * AIRBORNE_LOST
        * AIRBORNE_EXIT
    """

    _VALID_SUBSTATES = {
        AirborneSubState.AIRBORNE_HOLD,
        AirborneSubState.AIRBORNE_MISSION,
        AirborneSubState.AIRBORNE_LOST,
        AirborneSubState.AIRBORNE_EXIT,
    }

    def __init__(self, model, state_map, initial_state):
        self.model = model

        # Nur gültige Substates übernehmen
        self.state_map = {
            key: value
            for key, value in state_map.items()
            if key in self._VALID_SUBSTATES
        }

        # Initialer Substate
        self.active_substate = initial_state
        self.active_fsm = self.state_map[self.active_substate](self.model)

    # ------------------------------------------------------------
    # FSM-Tick
    # ------------------------------------------------------------
    def step(self):
        """
        Führt einen Tick der aktiven SubFSM aus.
        Gibt den resultierenden Substate zurück.
        """
        next_sub = self.active_fsm.on_update()

        if next_sub not in self._VALID_SUBSTATES:
            return self.active_substate

        if next_sub != self.active_substate:
            self.active_substate = next_sub
            self.active_fsm = self.state_map[self.active_substate](self.model)

        return self.active_substate

    # ------------------------------------------------------------
    # Events
    # ------------------------------------------------------------
    def handle_event(self, event):
        next_sub = self.active_fsm.handle_event(event)

        if next_sub not in self._VALID_SUBSTATES:
            return self.active_substate

        if next_sub != self.active_substate:
            self.active_substate = next_sub
            self.active_fsm = self.state_map[self.active_substate](self.model)

        return self.active_substate
