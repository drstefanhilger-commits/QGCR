# === PFAD-B FULL FILE: QGCR/controller/main_controller.py ===

from QGCR.states.main_state import MainState


class MainController:
    """
    Top-Level Router für High-Level-FSMs.
    - KEIN FSM
    - KEIN Lifecycle
    - tickt nur die High-Level-FSM
    """

    def __init__(self, model, state_map):
        self.model = model
        self.state_map = state_map

        # Startzustand
        self.active_state = MainState.STARTUP
        self.active_fsm = self.state_map[self.active_state](model)

        # HFSM-State im Model sichtbar machen
        try:
            self.model.hfsm_main = self.active_state.name
            self.model.hfsm_sub = getattr(self.active_fsm, "active_substate", self.active_state).name
            self.model.push_state_update()
        except Exception:
            pass

    def on_update(self):
        """
        Tickt genau EINMAL die aktive High-Level-FSM.
        """

        next_state = self.active_fsm.on_update()

        # Kein Wechsel?
        if next_state == self.active_state:
            return

        # Wechsel möglich?
        if next_state in self.state_map:
            self._switch_to(next_state)

    def _switch_to(self, new_state):
        old = self.active_state
        self.active_state = new_state

        # Neues HFSM erzeugen
        self.active_fsm = self.state_map[new_state](self.model)

        # HFSM-State im Model + GUI sichtbar machen
        try:
            self.model.hfsm_main = new_state.name
            try:
                sub = self.active_fsm.active_substate.name
            except Exception:
                sub = new_state.name
            self.model.hfsm_sub = sub

            # Log für HFSM-Wechsel
            self.model.add_log(f"HFSM-Wechsel: {old.name} → {new_state.name}")

            # State an GUI pushen
            self.model.push_state_update()
        except Exception:
            pass

    def get_state_dict(self):
        """
        Liefert den aktuellen HFSM- und Substate für GUI.
        """
        try:
            sub = self.active_fsm.active_substate.name
        except Exception:
            sub = "-"

        return {
            "main": self.active_state.name,
            "sub": sub
        }
