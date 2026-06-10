class BaseMachineController:
    def __init__(self, model):
        self.model = model
        self.state_map = {}
        self.current_state = None

    def build_states(self):
        raise NotImplementedError

    def _transition(self, next_state):
        self.current_state = next_state

    # --------------------------------------------------------------
    # Tick-basierte Logik (HFSM.on_update)
    # --------------------------------------------------------------
    def step(self):
        fsm = self.state_map[self.current_state]
        next_state = fsm.on_update()

        if next_state != self.current_state:
            self._transition(next_state)

        return next_state

    # --------------------------------------------------------------
    # Event-basierte Logik (HFSM.handle_event)
    # --------------------------------------------------------------
    def process_event(self, event):
        """
        Leitet EIN Event an die aktuelle HFSM weiter.
        Die HFSM entscheidet, ob ein Statewechsel stattfindet.
        """
        fsm = self.state_map[self.current_state]
        next_state = fsm.handle_event(event)

        if next_state != self.current_state:
            self._transition(next_state)

        return next_state

    # --------------------------------------------------------------
    # Alle Events aus der State-Queue verarbeiten
    # --------------------------------------------------------------
    def process_all_events(self):
        """
        Holt ALLE Events aus model.queue_state und verarbeitet sie
        deterministisch in FIFO-Reihenfolge.
        """
        while True:
            try:
                event = self.model.queue_state.get_nowait()
            except Exception:
                break

            self.process_event(event)
