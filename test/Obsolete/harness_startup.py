#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/harness/harness_startup.py ===

import time

from QGCR.communication.qgc_connection import QGCConnection
from QGCR.communication.qgc_dispatcher import QGCDispatcher
from QGCR.model.qgc_model_router import QGCModelRouter

# Deine echten Klassen:
from QGCR.model.model import Model
from QGCR.states.startup.startup_hfsm import StartupHFSM


def main():
    print("[HARNESS] Starte Startup-Harness…")

    # ------------------------------------------------------------
    # 1) Dispatcher
    # ------------------------------------------------------------
    dispatcher = QGCDispatcher()

    # ------------------------------------------------------------
    # 2) Model
    # ------------------------------------------------------------
    model = Model()

    # ------------------------------------------------------------
    # 3) ModelRouter
    # ------------------------------------------------------------
    router = QGCModelRouter(model, dispatcher)
    router.register_all()

    # ------------------------------------------------------------
    # 4) StartupHFSM
    # ------------------------------------------------------------
    startup_hfsm = StartupHFSM(model)
    startup_hfsm.start()

    # ------------------------------------------------------------
    # 5) QGCConnection
    # ------------------------------------------------------------
    conn = QGCConnection(dispatcher)
    master, tsys, tcomp = conn.connect()

    print("[HARNESS] Verbindung steht. Warte auf StartupHFSM…")

    # ------------------------------------------------------------
    # 6) Warten bis Model PX4-Heartbeat meldet
    # ------------------------------------------------------------
    timeout = 10
    start = time.time()

    while time.time() - start < timeout:
        if model.px4_alive:
            print("[HARNESS] Model meldet PX4 alive.")
            break
        time.sleep(0.1)
    else:
        print("[HARNESS] ERROR: Model meldet KEIN PX4 alive.")
        return

    # ------------------------------------------------------------
    # 7) Warten bis StartupFSM READY ist
    # ------------------------------------------------------------
    timeout = 10
    start = time.time()

    while time.time() - start < timeout:
        if startup_fsm.is_ready():
            print("[HARNESS] StartupFSM ist READY.")
            break
        time.sleep(0.1)
    else:
        print("[HARNESS] ERROR: StartupFSM wurde NICHT READY.")
        return

    print("[HARNESS] Startup-Harness COMPLETE")


if __name__ == "__main__":
    main()
