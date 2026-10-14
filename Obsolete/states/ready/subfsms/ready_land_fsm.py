# === PFAD-B FULL FILE: QGCR/states/ready/subfsms/ready_land_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState

class ReadyLandFSM(BaseFSM):
    """
    LAND im READY-HFSM.
    Führt ein PX4-LAND-Kommando aus und kehrt danach nach READY_IDLE zurück.
    """

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_LAND)
        self._next_state = ReadySubState.READY_IDLE
        self._sent = False

    def _on_enter(self):
        super()._on_enter()
        self.model.log.qgcr("[READY_LAND] ENTER")

        try:
            self.model.connection.master.mav.command_long_send(
                self.model.target_system,
                self.model.target_component,
                21,  # MAV_CMD_NAV_LAND
                0,
                0, 0, 0, 0,
                float(self.model.home_lat or 0),
                float(self.model.home_lon or 0),
                float(self.model.home_alt or 0),
            )
            self._sent = True
            self.model.log.qgcr("[READY_LAND] LAND command sent")
        except Exception as e:
            self.model.log.qgcr(f"[READY_LAND] ERROR sending LAND: {e}")

    def _on_during(self):
        pass

    def _on_exit(self):
        self.model.log.qgcr("[READY_LAND] EXIT → READY_IDLE")
        return self._next_state
