# === PFAD-B FULL FILE: QGCR/states/ready/subfsms/ready_idle_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState


class ReadyIdleFSM(BaseFSM):
    """
    READY_IDLE:
    - Standardzustand im READY-HFSM
    - Wartet auf Benutzerinteraktion
    - Reagiert auf:
        * Heartbeat verloren → READY_HEARTBEAT_LOST
        * Mission geladen → READY_MISSION
        * TAKEOFF → READY_TAKEOFF
    """

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_IDLE)
        self._next_state = ReadySubState.READY_IDLE
        self._pending_event = None

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(("status", "Ready: Idle"))
        except Exception:
            pass

    def _on_during(self):
        """
        READY_IDLE reagiert auf:
        - Heartbeat verloren
        - Mission geladen
        - TAKEOFF
        - GUI-Events
        """

        # 1) Heartbeat verloren → nur, wenn wir schon mal einen hatten
        if self.model.px4_heartbeat_count > 0 and not self.model.px4_connected:
            self._next_state = ReadySubState.READY_HEARTBEAT_LOST
            return

        # 2) GUI-Events lesen
        self._pending_event = None
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

        # 3) Mission geladen → READY_MISSION
        if getattr(self.model, "mission_loaded", False):
            self._next_state = ReadySubState.READY_MISSION
            return

        # 4) TAKEOFF → READY_TAKEOFF
        if self._pending_event == "TAKEOFF":
            self._next_state = ReadySubState.READY_TAKEOFF
            return

        # 5) Mission-Tab geöffnet → READY_MISSION
        if self._pending_event == "GUI_TAB_MISSION":
            self._next_state = ReadySubState.READY_MISSION
            return

    def _on_exit(self):
        """
        Keine Exit-Logik. ReadyHFSM entscheidet High-Level-Wechsel.
        """
        return self._next_state
