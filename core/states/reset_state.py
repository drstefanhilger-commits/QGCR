# === PFAD-B FULL FILE: QGCR/states/reset_state.py ===

from QGCR.states.main_state import MainState


class ResetState:
    """
    Stoppt PX4-SITL Swarm, stoppt Simulator,
    archiviert Logs, löscht 2D-View.
    """

    def __init__(self, model):
        self.model = model
        self.active_substate = MainState.RESET

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def on_enter(self):
        self.model.log.qgcr("[Reset] entering ResetState")

        # Logs archivieren
        try:
            self.model.logging.close_and_archive()
        except Exception:
            pass

        # 2D-View löschen
        try:
            self.model.gui.clear_flight_view()
        except Exception:
            pass

        # PX4 Swarm stoppen
        try:
            if self.model.startup_controller:
                self.model.startup_controller.stop_all(kill=True)
        except Exception as e:
            self.model.log.qgcr(f"[Reset] stop error: {e}")

        # Flag setzen → MainController wechselt zu STARTUP
        self.model.reset_done = True

    # ------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------
    def on_update(self):
        return MainState.RESET

    # ------------------------------------------------------------
    # EXIT
    # ------------------------------------------------------------
    def on_exit(self):
        self.model.log.qgcr("[Reset] exiting ResetState")
