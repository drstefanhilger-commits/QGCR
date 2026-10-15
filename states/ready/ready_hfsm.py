# === PFAD-B FULL FILE: QGCR/states/ready/ready_hfsm.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM
from QGCR.model.mavlink_commands import cmd_arm, cmd_disarm
import time


class ReadyHFSM(BaseHFSM):

    def __init__(self, model):
        super().__init__(model, MainState.READY)
        self._next_state = MainState.READY
        self._enter_time = 0.0

    def _on_enter(self):
        self.model.log.qgcr("[ReadyHFSM] entering READY")
        self.model.hfsm_main = "READY"
        self.model.hfsm_sub = "IDLE"
        self.model.push_state_update()

        # Zeit merken für Grace-Phase
        self._enter_time = time.time()

        # Alte Events verwirft der MainController beim Wechsel nach READY –
        # NICHT hier, sonst gehen Klicks zwischen Wechsel und erstem Tick verloren.

    def _on_during(self):
        self.model.takeoff.tick()

        if self.model.hfsm_events:
            event = self.model.hfsm_events.popleft()

            match event:
                case "TAKEOFF":
                    self._next_state = MainState.AIRBORNE
                    return

                case "RESET":
                    self.model.log.qgcr("[ReadyHFSM] RESET received")
                    self._next_state = MainState.RESET
                    return

                case "ARM":
                    self._send_arm_disarm(arm=True)

                case "DISARM":
                    self._send_arm_disarm(arm=False)

        # Mission-Tab aktiv → MISSION, FSL-Tab aktiv → INTERCEPT (zustandsbasiert)
        if self.model.active_tab == "Mission":
            self._next_state = MainState.MISSION
            return
        if self.model.active_tab == "FSL":
            self._next_state = MainState.INTERCEPT
            return

        # Grace-Phase nach Startup/Reset
        if time.time() - self._enter_time < 5.0:
            self._next_state = MainState.READY
            return

        if not self.model.connection_ready():
            self.model.log.qgcr("[ReadyHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        self._next_state = MainState.READY

    def _on_exit(self):
        return self._next_state

    # ------------------------------------------------------------
    # ARM / DISARM (MAV_CMD_COMPONENT_ARM_DISARM)
    # ------------------------------------------------------------
    def _send_arm_disarm(self, arm):
        name = "ARM" if arm else "DISARM"

        connection = getattr(self.model, "connection", None)
        master = getattr(connection, "master", None)
        if master is None or not getattr(master, "target_system", 0):
            self.model.log.qgcr(f"[ReadyHFSM] {name} ignoriert: noch kein PX4-Ziel")
            return

        build = cmd_arm if arm else cmd_disarm
        connection.send(build(master.target_system, master.target_component))
        self.model.log.qgcr(f"[ReadyHFSM] {name} gesendet")
