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

    # ------------------------------------------------------------
    # GLOBAL EVENT HANDLING (NEU)
    # ------------------------------------------------------------
    def _process_global_events(self):
        if getattr(self.model, "reset_done", False):
            self.model.reset_done = False
            self._switch_to(MainState.STARTUP)
            return

        # Ganze Queue durchsuchen (nicht nur das erste Element): ein Event, das
        # der aktive Zustand nie liest (z. B. ARM in STARTUP), darf RESET nicht blockieren.
        for event in list(self.model.hfsm_events):
            if event == "TAKEOFF_DONE":
                self.model.hfsm_events.remove(event)
                if self.active_state != MainState.AIRBORNE:
                    self._switch_to(MainState.AIRBORNE)
                return

            # RESET im Flug übernimmt die HFSM selbst (erst landen, dann RESET)
            if event == "RESET" and self.active_state not in (MainState.AIRBORNE, MainState.INTERCEPT):
                self.model.hfsm_events.remove(event)
                self._switch_to(MainState.RESET)
                return

            if event == "RESET_DONE":
                self.model.hfsm_events.remove(event)
                self._switch_to(MainState.STARTUP)
                return

    # ------------------------------------------------------------
    # MAIN UPDATE
    # ------------------------------------------------------------
    def on_update(self):
        """
        Tickt genau EINMAL die aktive High-Level-FSM.
        """
        # print("[MAIN DEBUG] HFSM active:", type(self.active_fsm).__name__)

        # 1) Globale Events zuerst
        self._process_global_events()

        # 2) Dann aktiven HFSM ticken
        next_state = self.active_fsm.on_update()

        # Kein Wechsel?
        if next_state == self.active_state:
            return

        # Wechsel möglich?
        if next_state in self.state_map:
            self._switch_to(next_state)

    # ------------------------------------------------------------
    # STATE SWITCH
    # ------------------------------------------------------------
    def _switch_to(self, new_state):
        old = self.active_state
        self.active_state = new_state

        # READY: alte Events (z. B. TAKEOFF aus dem Vorzyklus) verwerfen –
        # hier, BEVOR hfsm_main = READY sichtbar wird. Ein Klick, den die GUI
        # danach sendet, bleibt erhalten.
        if new_state == MainState.READY:
            self.model.hfsm_events.clear()

        # Neues HFSM erzeugen
        self.active_fsm = self.state_map[new_state](self.model)

        # StartupController-Referenz ins Model übernehmen
        if hasattr(self.active_fsm, "startup_controller"):
            self.model.startup_controller = self.active_fsm.startup_controller

        # HFSM-State im Model + GUI sichtbar machen
        try:
            self.model.hfsm_main = new_state.name
            try:
                sub = self.active_fsm.active_substate.name
            except Exception:
                sub = new_state.name
            self.model.hfsm_sub = sub

            # Log für HFSM-Wechsel
            self.model.log.qgcr(f"HFSM-Wechsel: {old.name} → {new_state.name}")

            # State an GUI pushen
            self.model.push_state_update()
        except Exception:
            pass

    # ------------------------------------------------------------
    # GUI State Dict
    # ------------------------------------------------------------
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
