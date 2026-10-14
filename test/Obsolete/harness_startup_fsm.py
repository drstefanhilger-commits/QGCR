#!/usr/bin/env python3
"""
StartupFSM-Harness (refaktoriert):
Testet die komplette Startup-Pipeline gegen eine echte PX4-SITL Instanz.
"""

from harness.harness_px4_alive import require_px4_alive

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.startup_substate import SubState
from QGCR.states.main_state import MainState

from QGCR.communication.microservices.param_microservice import ParamMicroService
from QGCR.communication.microservices.home_microservice import HomeMicroService
from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.communication.connection import Connection


# ------------------------------------------------------------
# Services-Container (realitätsnah)
# ------------------------------------------------------------
class Services:
    def __init__(self, master, tsys, tcomp, connection):
        self.connection = connection
        self.param = ParamMicroService(master, tsys, tcomp)
        self.home = HomeMicroService(master, tsys, tcomp)
        self.mission = MissionMicroService(master, tsys, tcomp)


# ------------------------------------------------------------
# Minimal Model für den Test (GUI-kompatibel)
# ------------------------------------------------------------
class StartupTestModel:
    def __init__(self, services):
        self.services = services

        self.params = None
        self.home = None
        self.mission = None

        # GUI-Queue (Dummy)
        class DummyQueue:
            def push(self, msg):
                print(f"[GUI] {msg}")

        class DummyRegistry:
            gui = DummyQueue()

        self.queue_registry = DummyRegistry()

    def update_status(self, msg):
        print(f"[STATUS] {msg}")


# ------------------------------------------------------------
# State Map für StartupController
# ------------------------------------------------------------
from QGCR.states.startup.subfsms.startup_heartbeat_fsm import StartupHeartbeatFSM
from QGCR.states.startup.subfsms.startup_param_sync_fsm import StartupParamSyncFSM
from QGCR.states.startup.subfsms.startup_home_fsm import StartupHomeFSM
from QGCR.states.startup.subfsms.startup_mission_fsm import StartupMissionFSM
from QGCR.states.startup.subfsms.startup_ok_fsm import StartupOKFSM

STATE_MAP = {
    SubState.STARTUP_HEARTBEAT: StartupHeartbeatFSM,
    SubState.STARTUP_PARAMS: StartupParamSyncFSM,
    SubState.STARTUP_HOME: StartupHomeFSM,
    SubState.STARTUP_MISSION: StartupMissionFSM,
    SubState.STARTUP_OK: StartupOKFSM,
}


# ------------------------------------------------------------
# Harness
# ------------------------------------------------------------
def main():
    print("[HARNESS] Starte StartupFSM-Harness…")

    # 1) PX4 Alive prüfen
    master, tsys, tcomp = require_px4_alive()

    # 2) Connection-Wrapper erzeugen
    conn = Connection()
    conn.master = master
    conn.target_system = tsys
    conn.target_component = tcomp

    # 3) Services erzeugen
    services = Services(master, tsys, tcomp, conn)

    # 4) Model erzeugen
    model = StartupTestModel(services)

    # 5) StartupHFSM erzeugen
    fsm = StartupHFSM(model, STATE_MAP)

    # 6) StartupHFSM laufen lassen
    print("[HARNESS] Starte StartupHFSM…")

    for _ in range(50):
        state = fsm.on_update()
        if state == MainState.READY:
            break

    # 7) Ergebnis prüfen
    print(f"[HARNESS] High-Level-State: {state}")

    if state != MainState.READY:
        print("[HARNESS] FEHLER: StartupFSM hat READY NICHT erreicht.")
        return

    print("[HARNESS] StartupFSM hat READY erreicht.")

    # 8) Model prüfen
    print(f"[HARNESS] Parameter geladen: {len(model.params) if model.params else 0}")
    print(f"[HARNESS] Home: {model.home}")
    print(f"[HARNESS] Mission Items: {len(model.mission) if model.mission else 0}")

    print("[HARNESS] StartupFSM-Harness COMPLETE")


if __name__ == "__main__":
    main()
