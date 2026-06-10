# === PFAD-B FULL FILE: test/test_airborne_sequence.py ===

from collections import deque

from QGCR.states.main_state import MainState
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM


class FakeQueueRegistry:
    """Simuliert GUI-Queue-Ausgaben."""
    def __init__(self):
        self.gui = deque()

    def require(self, name):
        assert name == "gui"
        return self

    def push(self, item):
        print(f"[GUI] {item}")
        self.gui.append(item)


class FakeModel:
    """Minimalmodell für HFSM-Tests."""
    def __init__(self):
        self.gui_events = deque()
        self.hfsm_events = deque()
        self.queue_registry = FakeQueueRegistry()

        # PX4-Status
        self.px4_connected = True
        self.px4_heartbeat_count = 1

        # Telemetrie
        self.vehicle_alt = 0.0

        # Mission-Status
        self.mission_loaded = False


def tick_fsm(fsm):
    """Tickt eine HFSM-Instanz."""
    next_state = fsm.on_update()
    return next_state


def run_test_sequence():
    print("\n=== AUTOMATISCHE AIRBORNE-TESTSEQUENZ ===\n")

    model = FakeModel()

    # HFSMs
    ready = ReadyHFSM(model)
    airborne = AirborneHFSM(model)

    # Start im READY
    active_hfsm = ready
    main_state = MainState.READY

    print("STATE = READY\n")

    # ------------------------------------------------------------
    # 1) TAKEOFF drücken
    # ------------------------------------------------------------
    print(">>> EVENT: TAKEOFF")
    model.gui_events.append("TAKEOFF")

    next_state = tick_fsm(active_hfsm)

    if next_state == MainState.AIRBORNE:
        print("HFSM-Wechsel: READY → AIRBORNE\n")
        active_hfsm = airborne
        main_state = MainState.AIRBORNE

    # ------------------------------------------------------------
    # 2) TAKEOFF-Phase simulieren (Höhe steigt)
    # ------------------------------------------------------------
    print(">>> SIM: Höhe steigt…")
    for alt in [0.5, 1.2, 3.0, 6.0]:
        model.vehicle_alt = alt
        tick_fsm(active_hfsm)

    # ------------------------------------------------------------
    # 3) HOLD drücken
    # ------------------------------------------------------------
    print("\n>>> EVENT: HOLD")
    model.gui_events.append("HOLD")
    tick_fsm(active_hfsm)

    # ------------------------------------------------------------
    # 4) RESUME drücken
    # ------------------------------------------------------------
    print("\n>>> EVENT: RESUME")
    model.gui_events.append("RESUME")
    tick_fsm(active_hfsm)

    # ------------------------------------------------------------
    # 5) LAND drücken
    # ------------------------------------------------------------
    print("\n>>> EVENT: LAND")
    model.gui_events.append("LAND")
    tick_fsm(active_hfsm)

    # ------------------------------------------------------------
    # 6) EXIT → zurück zu READY
    # ------------------------------------------------------------
    print("\n>>> EXIT-Phase ticken…")
    next_state = tick_fsm(active_hfsm)

    if next_state == MainState.READY:
        print("HFSM-Wechsel: AIRBORNE → READY\n")
        active_hfsm = ready
        main_state = MainState.READY

    print("=== TESTSEQUENZ BEENDET ===\n")


if __name__ == "__main__":
    run_test_sequence()
