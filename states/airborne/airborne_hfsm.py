# === PFAD-B FULL FILE: QGCR/states/airborne/airborne_hfsm.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM
from QGCR.model.mavlink_commands import cmd_land


class AirborneHFSM(BaseHFSM):
    """
    AIRBORNE:
    - Enter: Takeoff-MicroService starten (falls IDLE)
    - LAND  → MAV_CMD_NAV_LAND, hfsm_sub = LAND; nach Landung (PX4 disarmt) → READY
    - RESET / Verbindung verloren → RESET
    """

    def __init__(self, model):
        super().__init__(model, MainState.AIRBORNE)
        self._next_state = MainState.AIRBORNE
        self._landing = False

    def _on_enter(self):
        self.model.log.qgcr("[AirborneHFSM] entering AIRBORNE")
        self.model.hfsm_main = "AIRBORNE"
        self.model.hfsm_sub = "FLIGHT"
        self.model.push_state_update()
        if self.model.takeoff.state == self.model.takeoff.STATE_IDLE:
            self.model.takeoff.start()
            self.model.log.qgcr("[AirborneHFSM] TAKEOFF Microservice started")

    def _on_during(self):
        self.model.takeoff.tick()

        if self.model.hfsm_events:
            event = self.model.hfsm_events.popleft()

            match event:
                case "RESET":
                    self.model.log.qgcr("[AirborneHFSM] RESET received")
                    self._next_state = MainState.RESET
                    return

                case "LAND":
                    self._start_landing()

        if not self.model.connection_ready():
            self.model.log.qgcr("[AirborneHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        # Landung abgeschlossen: PX4 disarmt nach dem Aufsetzen selbst
        if self._landing and not self.model.px4_armed:
            self.model.log.qgcr("[AirborneHFSM] gelandet und disarmed → READY")
            self._reset_takeoff()
            self._next_state = MainState.READY
            return

        self._next_state = MainState.AIRBORNE

    def _on_exit(self):
        return self._next_state

    # ------------------------------------------------------------
    # LAND
    # ------------------------------------------------------------
    def _start_landing(self):
        if self._landing:
            self.model.log.qgcr("[AirborneHFSM] LAND ignoriert: Landung läuft bereits")
            return

        connection = getattr(self.model, "connection", None)
        master = getattr(connection, "master", None)
        if master is None or not getattr(master, "target_system", 0):
            self.model.log.qgcr("[AirborneHFSM] LAND ignoriert: noch kein PX4-Ziel")
            return

        # Laufende Takeoff-Sequenz nicht weiterführen
        self._reset_takeoff()

        connection.send(cmd_land(master.target_system, master.target_component))
        self._landing = True
        self.model.hfsm_sub = "LAND"
        self.model.push_state_update()
        self.model.log.qgcr("[AirborneHFSM] LAND gesendet")

    def _reset_takeoff(self):
        takeoff = self.model.takeoff
        if hasattr(takeoff, "reset"):
            takeoff.reset()
