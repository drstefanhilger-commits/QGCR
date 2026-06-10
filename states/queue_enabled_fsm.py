# === PFAD-B FULL FILE: QGCR/states/queue_enabled_fsm.py ===

from QGCR.states.base_fsm import BaseFSM


class QueueEnabledFSM(BaseFSM):
    """
    FSM mit QueueRegistry-Integration.
    Infrastruktur-Schicht, optional.
    """

    def __init__(self, model, state_enum, queue_registry):
        super().__init__(model, state_enum)
        self.queue_registry = queue_registry

    def emit_gui(self, event_type, payload):
        """
        Sendet ein GUI-Event in die GUI-Queue.
        """
        try:
            self.queue_registry.require("gui").push((event_type, payload))
        except Exception:
            pass

    def emit_fsm(self, event_type, payload):
        """
        Sendet ein FSM-Event in die FSM-Queue.
        """
        try:
            self.queue_registry.require("fsm").push((event_type, payload))
        except Exception:
            pass
