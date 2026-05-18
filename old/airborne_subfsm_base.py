# === PFAD-B FULL FILE: airborne_subfsm_base.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.airborne.airborne_events import (
    AirborneEvent,
    AirborneEventType,
    AirborneEvents
)


class AirborneSubFSM(BaseFSM):
    """
    Gemeinsame Basisklasse für alle Airborne-Sub-FSMs.
    Bietet einheitliches Event-Handling.
    """

    def __init__(self, model, state_enum):
        super().__init__(model, state_enum)
        self._event_queue = []
        self._next_state = state_enum

    # ------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------
    def handle_event(self, event: AirborneEvent):
        """
        Events werden in die Queue gelegt.
        Verarbeitung erfolgt deterministisch in _on_during().
        """
        self._event_queue.append(event)

    def _process_next_event(self):
        """
        Verarbeitet pro Tick genau ein Event.
        """
        if not self._event_queue:
            return None

        event = self._event_queue.pop(0)
        return self._handle_event(event)

    # ------------------------------------------------------------
    # Default-Implementierungen für BaseFSM
    # ------------------------------------------------------------
    def _on_enter(self):
        pass

    def _on_exit(self):
        """
        MUSS self._next_state zurückgeben.
        """
        return self._next_state

    # ------------------------------------------------------------
    # Override in Sub-FSMs
    # ------------------------------------------------------------
    def _handle_event(self, event: AirborneEvent):
        """
        Wird von Sub-FSMs überschrieben.
        """
        return None
