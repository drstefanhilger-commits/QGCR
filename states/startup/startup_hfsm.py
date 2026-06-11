# === PFAD-B FULL FILE: QGCR/states/startup/startup_hfsm.py ===

import time
from QGCR.states.base_hfsm import BaseHFSM
from QGCR.states.main_state import MainState
from QGCR.sim.px4_swarm_starter import PX4InstanceConfig


class StartupHFSM(BaseHFSM):
    """
    Startup-HFSM:
    - Liest Setup-Daten aus model.scenario
    - Baut PX4InstanceConfig-Liste
    - Startet PX4 über swarm_starter
    - Wartet auf Heartbeat / ParamSync / MissionLoad
    - Übergang nach READY
    """

    def __init__(self, model):
        super().__init__(model, MainState.STARTUP)
        self._next_state = MainState.STARTUP
        self._phase = "INIT"
        self._start_time = 0

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def _on_enter(self):
        self.model.hfsm_main = "STARTUP"
        self.model.hfsm_sub = "INIT"
        self.model.push_state_update()

        self._phase = "INIT"
        self._start_time = time.time()

        # --------------------------------------------------------
        # 1) Setup-Daten aus dem Model lesen
        # --------------------------------------------------------
        scenario = getattr(self.model, "scenario", None)

        if scenario is None or not hasattr(scenario, "uavs"):
            print("[StartupHFSM] WARNUNG: Keine Scenario-Daten gefunden.")
            self._next_state = MainState.READY
            return

        # --------------------------------------------------------
        # 2) PX4InstanceConfig-Liste erzeugen
        # --------------------------------------------------------
        instance_configs = []
        instance_id = 1

        for uav in scenario.uavs:
            cfg = PX4InstanceConfig(
                px4_dir=uav["px4_dir"],
                model_name=uav["uav_type"],
                instance_id=instance_id,
                verbose=True
            )
            instance_configs.append(cfg)
            instance_id += 1

        # --------------------------------------------------------
        # 3) SwarmStarter konfigurieren
        # --------------------------------------------------------
        self.model.vehicle_configs = instance_configs
        self.model.swarm_starter.instances = instance_configs

        # --------------------------------------------------------
        # 4) PX4 starten
        # --------------------------------------------------------
        print("[StartupHFSM] Starte PX4-Instanzen…")
        self.model.swarm_starter.start_all()

        self._phase = "WAIT_HEARTBEAT"
        self.model.hfsm_sub = "WAIT_HEARTBEAT"
        self.model.push_state_update()

    # ------------------------------------------------------------
    # DURING
    # ------------------------------------------------------------
    def _on_during(self):

        # RESET → sofort zurück nach SETUP
        if self._pop_event("RESET"):
            self._next_state = MainState.SETUP
            return

        # --------------------------------------------------------
        # PHASE 1: Heartbeat abwarten
        # --------------------------------------------------------
        if self._phase == "WAIT_HEARTBEAT":
            if getattr(self.model, "px4_connected", False):
                print("[StartupHFSM] PX4 Heartbeat empfangen.")
                self._phase = "PARAMSYNC"
                self.model.hfsm_sub = "PARAMSYNC"
                self.model.push_state_update()
            return

        # --------------------------------------------------------
        # PHASE 2: ParamSync (Platzhalter)
        # --------------------------------------------------------
        if self._phase == "PARAMSYNC":
            # Später: echtes ParamSync-Event
            time.sleep(0.3)
            print("[StartupHFSM] ParamSync OK.")
            self._phase = "MISSION"
            self.model.hfsm_sub = "MISSION"
            self.model.push_state_update()
            return

        # --------------------------------------------------------
        # PHASE 3: MissionLoad (Platzhalter)
        # --------------------------------------------------------
        if self._phase == "MISSION":
            # Später: Missionsdatei pro UAV laden
            time.sleep(0.3)
            print("[StartupHFSM] MissionLoad OK.")
            self._phase = "DONE"
            self.model.hfsm_sub = "DONE"
            self.model.push_state_update()
            return

        # --------------------------------------------------------
        # PHASE 4: DONE → READY
        # --------------------------------------------------------
        if self._phase == "DONE":
            self._next_state = MainState.READY
            return

    # ------------------------------------------------------------
    # EXIT
    # ------------------------------------------------------------
    def _on_exit(self):
        return self._next_state
