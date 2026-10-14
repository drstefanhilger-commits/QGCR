# === PFAD-B FULL FILE: QGCR/states/startup/subfsms/startup_mission_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.startup.startup_substate import StartupSubState


class StartupMissionFSM(BaseFSM):
    """
    Lädt die Mission synchron über den MissionMicroService (download()).
    Kein asynchrones Warten, kein start_download().
    """

    def __init__(self, model):
        super().__init__(model, StartupSubState.STARTUP_MISSION)
        self._done = False

    def _on_enter(self):
        """
        Mission synchron laden.
        """
        self._done = False

        # Mission im Model löschen
        self.model.clear_mission()

        # GUI-Status
        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Startup: Mission-Download gestartet")
            )
        except Exception:
            pass

        msgs = []
        try:
            # SYNCHRONER Download (Harness-kompatibel)
            msgs = self.model.mission_ms.download()
        except Exception as e:
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", f"Startup: Mission-Download Fehler: {e}")
                )
            except Exception:
                pass
            msgs = []

        # Logging
        try:
            self.model.queue_registry.require("gui").push(
                ("log", f"MissionDownload: {len(msgs)} items")
            )
            for m in msgs:
                self.model.queue_registry.require("gui").push(
                    ("log", f"WP seq={m.seq} cmd={m.command} x={m.x} y={m.y} z={m.z}")
                )
        except Exception:
            pass

        # Ins Model schreiben
        for m in msgs:
            self.model.add_mission_item(m.seq, m.command, m.x, m.y, m.z)

        # Flag setzen
        if len(msgs) > 0:
            self.model.mission.ready = True

        # Substate abgeschlossen
        self._done = True

        try:
            self.model.queue_registry.require("gui").push(
                ("status", f"Startup: Mission-Download abgeschlossen ({len(msgs)} WPs)")
            )
        except Exception:
            pass

    def _on_during(self):
        """
        Keine laufende FSM – alles passiert in _on_enter().
        """
        pass

    def _on_exit(self):
        """
        Weiter nach STARTUP_OK, wenn Download abgeschlossen.
        """
        if not self._done:
            return StartupSubState.STARTUP_MISSION

        return StartupSubState.STARTUP_OK
