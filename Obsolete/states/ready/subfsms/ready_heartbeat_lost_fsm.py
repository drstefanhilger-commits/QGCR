# === PFAD-B FULL FILE: QGCR/states/ready/subfsms/ready_heartbeat_lost_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.ready.ready_substate import ReadySubState


class ReadyHeartbeatLostFSM(BaseFSM):
    """
    READY_HEARTBEAT_LOST:
    - Wird aktiv, wenn kein PX4-Heartbeat mehr empfangen wird.
    - Zeigt einen Fehlerstatus an.
    - Bleibt in diesem Zustand, bis die übergeordnete HFSM eingreift.
    - Keine automatische Erholung.
    """

    def __init__(self, model):
        super().__init__(model, ReadySubState.READY_HEARTBEAT_LOST)

        # Event-Puffer
        self._pending_event = None

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        """
        GUI informieren und Fehlerstatus setzen.
        Keine automatische Erholung.
        """

        try:
            self.model.queue_registry.require("gui").push(
                ("status", "FEHLER: PX4 Heartbeat verloren!")
            )
        except Exception:
            pass

        try:
            self.model.queue_registry.require("gui").push(
                ("log", "READY_HEARTBEAT_LOST: Heartbeat lost")
            )
        except Exception:
            pass

        try:
            self.model.queue_registry.require("gui").push(("disable", "takeoff"))
            self.model.queue_registry.require("gui").push(("disable", "land"))
        except Exception:
            pass

    def _on_during(self):
        """
        READY_HEARTBEAT_LOST sammelt nur Events.
        Keine automatische Erholung.
        """

        # GUI-Event lesen (falls später relevant)
        self._pending_event = None
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

        # Keine Statewechsel hier!

    def _on_exit(self):
        """
        EINZIGER Ort für Sub-State-Wechsel.
        Aber: READY_HEARTBEAT_LOST bleibt stabil.
        Die übergeordnete HFSM entscheidet den High-Level-Wechsel.
        """
        return ReadySubState.READY_HEARTBEAT_LOST
