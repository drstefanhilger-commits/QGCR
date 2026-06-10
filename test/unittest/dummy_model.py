# === PFAD-B FULL FILE: dummy_model.py ===

from queue import Queue
from QGCR.states.startup.startup_state_map import STARTUP_STATE_MAP
from QGCR.states.ready.ready_state_map import READY_STATE_MAP
from QGCR.states.startup.startup_state_map import STARTUP_STATE_MAP


class DummyModel:
    """
    Minimalmodell für FSM-Tests.
    Stellt nur die Felder bereit, die die Startup- und Ready-FSM benötigen.
    """

    def __init__(self):
        # ------------------------------------------------------------
        # Event-Queue (Startup-FSM)
        # ------------------------------------------------------------
        self.event_queue = Queue()

        # ------------------------------------------------------------
        # GUI-Queue (Ready-FSM)
        # ------------------------------------------------------------
        self.queue_gui = Queue()

        # ------------------------------------------------------------
        # Ready-FSM Flags
        # ------------------------------------------------------------
        self.takeoff_requested = False
        self.mission_requested = False

        # ------------------------------------------------------------
        # Heartbeat-Status (Startup-FSM)
        # ------------------------------------------------------------
        self.px4_heartbeat_ok = True

        # ------------------------------------------------------------
        # State Maps (HFSM benötigt diese!)
        # ------------------------------------------------------------
        self.startup_state_map = STARTUP_STATE_MAP
        self.ready_state_map = READY_STATE_MAP

        # ------------------------------------------------------------
        # Optional: Mission-Flags (falls FSM sie prüft)
        # ------------------------------------------------------------
        self.mission_uploaded = False
        self.mission_active = False

        # ------------------------------------------------------------
        # Startup map
        # ------------------------------------------------------------
        self.startup_state_map = STARTUP_STATE_MAP
