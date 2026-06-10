# === PFAD-B FULL FILE: QGCR/states/base_hfsm.py ===

from QGCR.states.base import Base

class BaseHFSM(Base):
    """
    Gemeinsame Basis für alle High-Level-FSMs (STARTUP, READY, MISSION, AIRBORNE).
    - Setzt model.hfsm_main beim Betreten
    - Enthält zentrale Logik für:
        * SubFSM-Erzeugung
        * Fehler-Logging bei fehlenden SubFSMs
        * Fallback auf default_substate
        * Warnung bei unverarbeiteten Events
    """

    def __init__(self, model, main_state):
        super().__init__(model, main_state)
        self.main_state = main_state

        # Von Kindklassen zu setzen:
        self.state_map = {}
        self.active_substate = None
        self.active_fsm = None
        self.default_substate = None

        self._pending_event = None
        self._next_state = main_state

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def _on_enter(self):
        self.model.hfsm_main = self.main_state.name
        self.model.push_state_update()

    # ------------------------------------------------------------
    # DURING (Kindklassen überschreiben nur Event-Switch)
    # ------------------------------------------------------------
    def _on_during(self):
        pass

    # ------------------------------------------------------------
    # SubFSM-Erzeugung (zentralisiert)
    # ------------------------------------------------------------
    def _create_subfsm_for_active_substate(self):
        if self.active_substate not in self.state_map:
            self.model.log.qgcr(
                f"[{self.__class__.__name__}] WARN: Kein SubFSM für {self.active_substate} in state_map"
            )

            if self.default_substate is not None:
                self.model.log.qgcr(
                    f"[{self.__class__.__name__}] Fallback → {self.default_substate}"
                )
                self.active_substate = self.default_substate
            else:
                self.model.log.qgcr(
                    f"[{self.__class__.__name__}] ERROR: Kein default_substate definiert"
                )
                return

        fsm_class = self.state_map[self.active_substate]
        self.active_fsm = fsm_class(self.model)

    # ------------------------------------------------------------
    # Event-Warnung
    # ------------------------------------------------------------
    def _warn_unhandled_event(self, event):
        self.model.log.qgcr(
            f"[{self.__class__.__name__}] WARN: Event '{event}' wurde nicht verarbeitet"
        )

    # ------------------------------------------------------------
    # EXIT
    # ------------------------------------------------------------
    def _on_exit(self):
        return self._next_state
