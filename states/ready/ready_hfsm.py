# === PFAD-B FULL FILE: QGCR/states/ready/ready_hfsm.py ===

from QGCR.states.base_hfsm import BaseHFSM
from QGCR.states.main_state import MainState
from QGCR.states.ready.ready_substate import ReadySubState
from QGCR.states.ready.ready_state_map import READY_STATE_MAP


class ReadyHFSM(BaseHFSM):
    """
    High-Level FSM für READY.
    """

    def __init__(self, model, state_map=None):
        super().__init__(model, MainState.READY)

        self.state_map = state_map if state_map is not None else READY_STATE_MAP
        self.active_substate = ReadySubState.READY_IDLE
        self.active_fsm = None
        self._next_state = MainState.READY
        self._pending_event = None

    def _create_subfsm_for_active_substate(self):
        fsm_class = self.state_map[self.active_substate]
        self.active_fsm = fsm_class(self.model)

    def _on_enter(self):
        super()._on_enter()
        self._create_subfsm_for_active_substate()

    def _on_during(self):
        next_sub = self.active_fsm.on_update()

        if next_sub is not None and next_sub != self.active_substate:
            self.active_substate = next_sub
            self._create_subfsm_for_active_substate()

        self._pending_event = None
        try:
            self._pending_event = self.model.hfsm_events.popleft()
        except Exception:
            self._pending_event = None

    def _on_exit(self):
        if not self.model.px4_connected:
            self._next_state = MainState.STARTUP

        elif self._pending_event == "EV_GOTO_MISSION":
            self._next_state = MainState.MISSION

        elif self._pending_event == "TAKEOFF":
            self._next_state = MainState.AIRBORNE

        return super()._on_exit()
