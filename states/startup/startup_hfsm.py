# === PFAD-B FULL FILE: QGCR/states/startup/startup_hfsm.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM
from QGCR.sim.px4_swarm_starter import PX4SwarmStarter


class StartupHFSM(BaseHFSM):

    def __init__(self, model):
        super().__init__(model, MainState.STARTUP)
        self._next_state = MainState.STARTUP
        self.startup_controller = None
        self._initialized = False

    def _on_enter(self):
        self.model.log.qgcr("[StartupHFSM] entering STARTUP")
        self.model.hfsm_main = "STARTUP"
        self.model.hfsm_sub = "INIT"
        self.model.push_state_update()

        # Wenn bereits ein Starter existiert → nicht neu starten
        if getattr(self.model, "startup_controller", None) is not None:
            self.model.log.qgcr(
                "[StartupHFSM] existing startup_controller found → reusing (no new start_all())"
            )
            self.startup_controller = self.model.startup_controller
            self._initialized = True
            return

        try:
            vehicle_configs = getattr(self.model, "vehicle_configs", [])
            self.startup_controller = PX4SwarmStarter(
                vehicle_configs,
                model=self.model,
            )
            self.startup_controller.start_all()
            self.model.startup_controller = self.startup_controller
            self.model.log.qgcr("[StartupHFSM] PX4SwarmStarter started")
        except Exception as e:
            self.model.log.qgcr(f"[StartupHFSM] PX4 start error: {e}")

        self._initialized = True

    def _on_during(self):
        if not self._initialized:
            self._next_state = MainState.STARTUP
            return

        if not self.model.connection_ready():
            self._next_state = MainState.STARTUP
            return

        if not self.model.heartbeat_ok():
            self._next_state = MainState.STARTUP
            return

        self.model.log.qgcr("[StartupHFSM] system ready → READY")
        self._next_state = MainState.READY

    def _on_exit(self):
        return self._next_state
