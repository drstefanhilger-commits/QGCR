# === PFAD-B FULL FILE: QGCR/states/airborne/airborne_hfsm.py ===

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM
from QGCR.model.mavlink_commands import cmd_land, cmd_mission_start


class AirborneHFSM(BaseHFSM):
    """
    AIRBORNE:
    - Enter: Takeoff-MicroService starten (falls IDLE) – nicht, wenn eine Mission läuft
    - LAND  → MAV_CMD_NAV_LAND, hfsm_sub = LAND; nach Landung (PX4 disarmt) → READY
    - MISSION_START → MAV_CMD_MISSION_START (AUTO.MISSION im Flug), hfsm_sub = MISSION;
      Mission endet mit Landung (PX4 disarmt) → READY
    - RESET / Verbindung verloren → RESET
    """

    def __init__(self, model):
        super().__init__(model, MainState.AIRBORNE)
        self._next_state = MainState.AIRBORNE
        self._landing = False
        self._seen_armed = False

    def _on_enter(self):
        self.model.log.qgcr("[AirborneHFSM] entering AIRBORNE")
        self.model.hfsm_main = "AIRBORNE"
        self.model.hfsm_sub = "MISSION" if self.model.mission_running else "FLIGHT"
        self.model.push_state_update()

        # Missionsstart vom Boden: PX4 fliegt selbst los, kein eigener Takeoff
        if self.model.mission_running:
            return

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

                case "MISSION_START":
                    self._start_mission()

        if not self.model.connection_ready():
            self.model.log.qgcr("[AirborneHFSM] Connection lost → RESET")
            self._next_state = MainState.RESET
            return

        # Landung abgeschlossen (LAND oder Missionsende): PX4 disarmt nach dem Aufsetzen selbst
        if self.model.px4_armed:
            self._seen_armed = True
        elif self._seen_armed and (self._landing or self.model.mission_running):
            self.model.log.qgcr("[AirborneHFSM] gelandet und disarmed → READY")
            self._reset_takeoff()
            self.model.mission_running = False
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

    # ------------------------------------------------------------
    # MISSION (im Flug)
    # ------------------------------------------------------------
    def _start_mission(self):
        if self.model.mission_running:
            self.model.log.qgcr("[AirborneHFSM] MISSION ignoriert: Mission läuft bereits")
            return

        if not self.model.mission.ready:
            self.model.log.qgcr("[AirborneHFSM] MISSION ignoriert: keine Mission geladen")
            return

        connection = getattr(self.model, "connection", None)
        master = getattr(connection, "master", None)
        if master is None or not getattr(master, "target_system", 0):
            self.model.log.qgcr("[AirborneHFSM] MISSION ignoriert: noch kein PX4-Ziel")
            return

        self._reset_takeoff()
        connection.send(cmd_mission_start(master.target_system, master.target_component))
        self.model.mission_running = True
        self.model.hfsm_sub = "MISSION"
        self.model.push_state_update()
        self.model.log.qgcr("[AirborneHFSM] MISSION_START gesendet")

    def _reset_takeoff(self):
        takeoff = self.model.takeoff
        if hasattr(takeoff, "reset"):
            takeoff.reset()
