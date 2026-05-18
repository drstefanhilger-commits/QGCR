# === PFAD-B FULL FILE: QGCR/states/airborne/airborne_hfsm.py ===

from QGCR.states.base_hfsm import BaseHFSM
from QGCR.states.main_state import MainState
from QGCR.states.airborne.airborne_substate import AirborneSubState
from QGCR.states.airborne.airborne_state_map import AIRBORNE_STATE_MAP


class AirborneHFSM(BaseHFSM):
    """
    High-Level FSM für AIRBORNE.
    """

    def __init__(self, model, state_map=None):
        super().__init__(model, MainState.AIRBORNE)

        self.state_map = state_map if state_map is not None else AIRBORNE_STATE_MAP
        self.active_substate = AirborneSubState.AIRBORNE_TAKEOFF
        self.active_fsm = None
        self._next_state = MainState.AIRBORNE
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

        elif self._pending_event == "EV_GOTO_READY":
            self._next_state = MainState.READY

        return super()._on_exit()
