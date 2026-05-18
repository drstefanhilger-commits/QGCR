from QGCR.events.event import Event, EventType


class EventRouter:
    """
    Der EventRouter ist die zentrale Stelle, an der alle State-Events
    (GUI → STATE, PX4 → STATE, interne Events) verarbeitet werden.

    Er hat KEINE Abhängigkeit zu:
    - GUI
    - MainWindow
    - Tabs
    - Widgets

    Er kommuniziert ausschließlich mit:
    - model.queue_state (Input)
    - MainStateMachineController (Output)
    """

    def __init__(self, model, controller):
        self.model = model
        self.controller = controller

    # --------------------------------------------------------------
    # Hauptschleife: Ein Event aus der State-Queue verarbeiten
    # --------------------------------------------------------------
    def process_next_event(self):
        """
        Holt EIN Event aus der State-Queue und verarbeitet es.
        Gibt den neuen MainState zurück.
        """
        try:
            event = self.model.queue_state.get_nowait()
        except Exception:
            return None  # Keine Events vorhanden

        return self.route_event(event)

    # --------------------------------------------------------------
    # Event → HFSM weiterleiten
    # --------------------------------------------------------------
    def route_event(self, event: Event):
        """
        Leitet ein Event an die aktuelle HFSM weiter.
        Die HFSM entscheidet, ob ein Statewechsel stattfindet.
        """
        fsm = self.controller.state_map[self.controller.current_state]

        # HFSM verarbeitet das Event
        next_state = fsm.handle_event(event)

        # Falls die HFSM einen Statewechsel wünscht
        if next_state != self.controller.current_state:
            self.controller._transition(next_state)

        return next_state
