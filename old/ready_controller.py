# === PFAD-B FULL FILE: QGCR/states/ready/ready_controller.py ===

from QGCR.states.ready.ready_substate import ReadySubState


class ReadyController:
    """
    Controller für die READY-SubFSMs.

    WICHTIG:
    - READY verwaltet ausschließlich Boden-/Bereitschaftsverhalten.
    - Mission-Operationen gehören NICHT in den READY-Zustand.
    - Daher akzeptiert dieser Controller nur:
        * READY_IDLE
        * READY_TAKEOFF
        * READY_HEARTBEAT_LOST
    """

    _VALID_SUBSTATES = {
        ReadySubState.READY_IDLE,
        ReadySubState.READY_TAKEOFF,
        ReadySubState.READY_HEARTBEAT_LOST,
    }

    def __init__(self, model, state_map):
        self.model = model

        # Map filtern → Mission wird entfernt, falls noch vorhanden
        self.state_map = {
            key: value
            for key, value in state_map.items()
            if key in self._VALID_SUBSTATES
        }

        # Start immer im READY_IDLE
        self.active_substate = ReadySubState.READY_IDLE
        self.active_fsm = self.state_map[self.active_substate](model)

    # ------------------------------------------------------------
    # FSM-Tick
    # ------------------------------------------------------------
    def step(self):
        next_sub = self.active_fsm.on_update()

        # Nur gültige READY-Substates akzeptieren
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

        # Nur gültige READY-Substates akzeptieren
        if next_sub not in self._VALID_SUBSTATES:
            return self.active_substate

        if next_sub != self.active_substate:
            self.active_substate = next_sub
            self.active_fsm = self.state_map[self.active_substate](self.model)

        return self.active_substate
