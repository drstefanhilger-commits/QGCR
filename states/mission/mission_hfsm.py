# === PFAD-B FULL FILE: QGCR/states/mission/mission_hfsm.py ===

from QGCR.states.base_hfsm import BaseHFSM
from QGCR.states.main_state import MainState
from QGCR.states.mission.mission_substate import MissionSubState
from QGCR.states.mission.mission_state_map import MISSION_STATE_MAP


class MissionHFSM(BaseHFSM):
    """
    High-Level FSM für MISSION.
    """

    def __init__(self, model, state_map=None):
        super().__init__(model, MainState.MISSION)

        self.state_map = state_map if state_map is not None else MISSION_STATE_MAP
        self.active_substate = MissionSubState.MISSION_IDLE
        self.active_fsm = None
        self._next_state = MainState.MISSION
        self._pending_event = None

    def _create_subfsm_for_active_substate(self):
        fsm_class = self.state_map[self.active_substate]
        self.active_fsm = fsm_class(self.model)

    def _on_enter(self):
        super()._on_enter()
        self._create_subfsm_for_active_substate()

        try:
            self.model.queue_registry.require("gui").push(("status", "Mission: Idle"))
        except Exception:
            pass

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
        try:
            if self._pending_event is not None:
                self.model.add_log(f"MISSION _on_exit pending_event={self._pending_event}")
        except Exception:
            pass

        if not self.model.px4_connected:
            self._next_state = MainState.STARTUP

        elif self._pending_event == "EV_GOTO_READY":
            self._next_state = MainState.READY

        elif self.active_substate == MissionSubState.MISSION_OK:
            self._next_state = MainState.READY

        elif self._pending_event == "TAKEOFF":
            self._next_state = MainState.AIRBORNE

        return super()._on_exit()
