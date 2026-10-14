# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_home_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState


class StartupHomeFSM(BaseFSM):
    """
    STARTUP_HOME:
    - wartet auf gültige Home-Position (lat/lon/alt)
    - kein Überspringen
    - kein Blockieren
    - Statewechsel erst, wenn Home empfangen wurde
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_HOME)

        self._pending_event = None
        self._lost_heartbeat = False
        self._home_received = False
        self._home_logged = False

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        """
        Home-Position wird jetzt NICHT mehr übersprungen.
        Wir warten auf die erste gültige HOME_POSITION Nachricht.
        """
        self._pending_event = None
        self._lost_heartbeat = False
        self._home_received = False

    def _on_during(self):
        """
        - prüft Heartbeat
        - prüft, ob Home-Position empfangen wurde
        """

        # Heartbeat verloren?
        if not self.model.px4_connected:
            self._lost_heartbeat = True
            return

        # Home empfangen?
        if (
            self.model.home_lat is not None
            and self.model.home_lon is not None
            and self.model.home_alt is not None
        ):
            self._home_received = True

        # GUI-Events ignorieren
        try:
            self._pending_event = self.model.gui_events.popleft()
        except Exception:
            pass

    def _on_exit(self):
        """
        EINZIGER Ort für Sub-State-Wechsel.
        """

        # 1) Heartbeat verloren → zurück zu STARTUP_HEARTBEAT
        if self._lost_heartbeat:
            try:
                self.model.log.qgcr("[STARTUP_HOME] Heartbeat verloren → STARTUP_HEARTBEAT")
                self.model.queue_registry.require("gui").push(
                    ("status", "Startup: Home-Schritt abgebrochen (Heartbeat verloren)")
                )
            except Exception:
                pass
            return StartupSubState.STARTUP_HEARTBEAT

        # 2) Home noch nicht empfangen → im selben State bleiben
        if not self._home_received:
            return StartupSubState.STARTUP_HOME

        # 3) Weiter zu Mission-Download
        try:
            if not self._home_logged:
                self._home_logged = True
                self.model.log.qgcr(
                    f"Home set: {self.model.home_lat:.5f}, "
                    f"{self.model.home_lon:.5f}, {self.model.home_alt:.1f} m"
                )
        except Exception:
            pass

        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Startup: Home-Position empfangen")
            )
        except Exception:
            pass

        return StartupSubState.STARTUP_MISSION
