# === PFAD-B FULL FILE: QGCR/states/ready/subfsms/ready_mission_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState


class ReadyMissionFSM(BaseFSM):
    """
    READY_MISSION:
    - User befindet sich im Mission-Tab
    - Mission kann hoch-/runtergeladen werden
    - KEIN Takeoff möglich
    - Wechsel zurück zu READY_IDLE, wenn GUI-Event 'GUI_TAB_HOME' kommt
    """

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_MISSION)

        # Event-Puffer
        self._pending_event = None

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Ready: Mission Tab")
            )
        except Exception:
            pass

    def _on_during(self):
        """
        READY_MISSION sammelt nur Informationen.
        Statewechsel passieren ausschließlich in _on_exit().
        """

        # GUI-Event lesen
        self._pending_event = None
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

        # Keine Statewechsel hier!
        # Nur Daten sammeln.

    def _on_exit(self):
        """
        EINZIGER Ort für Sub-State-Wechsel.
        """

        # 1) Heartbeat verloren → HEARTBEAT_LOST
        if self.model.px4_heartbeat_count > 0 and not self.model.px4_connected:
            return ReadySubState.READY_HEARTBEAT_LOST

        # 2) Tab-Wechsel zurück zu HOME → READY_IDLE
        if self._pending_event == "GUI_TAB_HOME":
            return ReadySubState.READY_IDLE

        # 3) Mission gelöscht → zurück zu READY_IDLE
        if not getattr(self.model, "mission_loaded", False):
            return ReadySubState.READY_IDLE

        # 4) TAKEOFF hier NICHT erlaubt → im Mission-Tab bleiben
        if self._pending_event == "TAKEOFF":
            return ReadySubState.READY_MISSION

        # 5) Standard: im Mission-Tab bleiben
        return ReadySubState.READY_MISSION
