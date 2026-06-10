# === PFAD-B FULL FILE: QGCR/states/startup_state.py ===

from QGCR.states.main_state import MainState
from sim.startup import StartupController


class StartupState:
    """
    Startet PX4-SITL Swarm (FW/MC/VTOL).
    Initialisiert danach Model + Microservices.
    """

    def __init__(self, model):
        self.model = model
        self.active_substate = MainState.STARTUP

        # Wird von ResetState gesetzt
        self.startup_controller = None

    # ------------------------------------------------------------
    # ENTER
    # ------------------------------------------------------------
    def on_enter(self):
        self.model.log.qgcr("[Startup] entering StartupState")

        # PX4 Swarm starten
        self.startup_controller = StartupController(self.model.vehicle_configs)
        self.startup_controller.start_all()

        # Microservices initialisieren
        try:
            self.model.connection.initialize()
            self.model.mission.initialize()
            self.model.telemetry.initialize()
        except Exception as e:
            self.model.log.qgcr(f"[Startup] Init error: {e}")

        # GUI informieren
        self.model.hfsm_main = "STARTUP"
        self.model.hfsm_sub = "INIT"
        self.model.push_state_update()

    # ------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------
    def on_update(self):
        """
        Wenn alles initialisiert ist → READY
        """
        if self.model.connection.is_ready():
            return MainState.READY

        return MainState.STARTUP

    # ------------------------------------------------------------
    # EXIT
    # ------------------------------------------------------------
    def on_exit(self):
        self.model.log.qgcr("[Startup] exiting StartupState")
