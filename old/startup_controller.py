# === PFAD-B FULL FILE: QGCR/states/startup/startup_controller.py ===

from QGCR.states.startup.startup_state_map import SubState, STARTUP_STATE_MAP


class StartupController:
    """
    Minimaler, autonomer Controller für die Startup-FSM-Kette.
    - Kennt seine SubStates selbst
    - Kennt die State-Map selbst
    - Kein externer initial_state
    - Kein externer state_map
    """

    def __init__(self, model):
        self.model = model

        # Initialer SubState ist immer HEARTBEAT
        self.current_state = SubState.STARTUP_HEARTBEAT

        # Aktive FSM instanziieren
        self.active_fsm = STARTUP_STATE_MAP[self.current_state](model)

    def step(self):
        """
        Führt einen Tick aus:
        - active_fsm.on_update() liefert next_state
        - Wenn next_state != current_state → neue FSM instanziieren
        """
        next_state = self.active_fsm.on_update()

        if next_state != self.current_state:
            self.current_state = next_state
            self.active_fsm = STARTUP_STATE_MAP[next_state](self.model)

        return self.current_state
