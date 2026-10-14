# === PFAD-B FULL FILE: QGCR/states/queue_enabled_state_machine.py ===

from QGCR.states.base_state_machine import BaseStateMachine


class QueueEnabledStateMachine(BaseStateMachine):
    """
    StateMachine mit QueueRegistry-Integration.
    Infrastruktur-Schicht, optional.
    """

    def __init__(self, model, queue_registry):
        super().__init__(model)
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
