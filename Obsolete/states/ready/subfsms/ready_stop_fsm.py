# === PFAD-B FULL FILE: QGCR/states/ready/subfsms/ready_stop_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState

class ReadyStopFSM(BaseFSM):
    """
    STOP im READY-HFSM.
    STOP bedeutet: Fahrzeug in HOLD bringen.
    Danach Rückkehr zu READY_IDLE.
    """

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_STOP)
        self._next_state = ReadySubState.READY_IDLE
        self._sent = False

    def _on_enter(self):
        super()._on_enter()
        self.model.log.qgcr("[READY_STOP] ENTER")

        try:
            # HOLD senden
            self.model.connection.master.mav.command_long_send(
                self.model.target_system,
                self.model.target_component,
                176,  # MAV_CMD_DO_SET_MODE
                0,
                4,    # HOLD mode
                0, 0, 0, 0, 0, 0
            )
            self._sent = True
            self.model.log.qgcr("[READY_STOP] HOLD command sent")
        except Exception as e:
            self.model.log.qgcr(f"[READY_STOP] ERROR sending HOLD: {e}")

    def _on_during(self):
        pass

    def _on_exit(self):
        self.model.log.qgcr("[READY_STOP] EXIT → READY_IDLE")
        return self._next_state
