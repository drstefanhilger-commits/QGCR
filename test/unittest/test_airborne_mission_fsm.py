# === PFAD-B FULL FILE: airborne_takeoff_fsm.py ===

from QGCR.states.airborne.subfsms.airborne_subfsm_base import AirborneSubFSM
from QGCR.states.airborne.airborne_substate import AirborneSubState
from QGCR.states.airborne.airborne_events import AirborneEvents


class AirborneTakeoffFSM(AirborneSubFSM):

    def __init__(self, model):
        super().__init__(model, AirborneSubState.AIRBORNE_TAKEOFF)
        self._next_state = AirborneSubState.AIRBORNE_TAKEOFF

        # Für Tests: Events, die ankommen
        self.events_received = []

    # ------------------------------------------------------------
    # PUBLIC EVENT HANDLER (vom Controller oder Test aufgerufen)
    # ------------------------------------------------------------
    def handle_event(self, event):
        """
        Tests erwarten:
        - Event wird registriert
        - Event landet in der internen Queue
        """
        # Test-Tracking
        try:
            self.events_received.append(event.name)
        except AttributeError:
            self.events_received.append(str(event))

        # WICHTIG: Event in interne Queue legen
        self._event_queue.append(event)

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def _on_enter(self):
        self._next_state = AirborneSubState.AIRBORNE_TAKEOFF

    # ------------------------------------------------------------
    # DURING
    # ------------------------------------------------------------
    def _on_during(self):
        event_result = self._process_next_event()

        if event_result is AirborneSubState.AIRBORNE_MISSION:
            self._next_state = AirborneSubState.AIRBORNE_MISSION
        else:
            self._next_state = AirborneSubState.AIRBORNE_TAKEOFF

    # ------------------------------------------------------------
    # EXIT
    # ------------------------------------------------------------
    def _on_exit(self):
        return self._next_state

    # ------------------------------------------------------------
    # Event-Handler
    # ------------------------------------------------------------
    def _handle_event(self, event):
        if event is AirborneEvents.TAKEOFF_COMPLETE:
            return AirborneSubState.AIRBORNE_MISSION
        return None
