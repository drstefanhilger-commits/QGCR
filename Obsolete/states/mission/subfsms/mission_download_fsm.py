# === PFAD-B FULL FILE: QGCR/states/mission/subfsms/mission_download_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.mission.mission_substate import MissionSubState


class MissionDownloadFSM(BaseFSM):
    """
    MISSION_DOWNLOAD:
    - Simulierter Download-Vorgang (Mockup)
    - Kein echter MAVLink-Download
    - Nach Abschluss → MISSION_IDLE
    """

    def __init__(self, model):
        super().__init__(model, MissionSubState.MISSION_DOWNLOAD)
        self._progress = 0
        self._done = False
        self._next_state = MissionSubState.MISSION_DOWNLOAD

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        self._progress = 0
        self._done = False

        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Mission: DOWNLOAD gestartet")
            )
        except Exception:
            pass

    def _on_during(self):
        """
        MOCKUP-Download:
        - zählt progress hoch
        - nach Erreichen von 100% → MISSION_IDLE
        """

        # Bereits abgeschlossen?
        if self._done:
            self._next_state = MissionSubState.MISSION_IDLE
            return

        # Fortschritt simulieren
        self._progress += 5

        try:
            self.model.queue_registry.require("gui").push(
                ("status", f"Mission: DOWNLOAD {self._progress}%")
            )
        except Exception:
            pass

        # Fertig?
        if self._progress >= 100:
            self._done = True
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", "Mission: DOWNLOAD abgeschlossen")
                )
            except Exception:
                pass

            self._next_state = MissionSubState.MISSION_IDLE
            return

        # Kein Substate-Wechsel
        self._next_state = MissionSubState.MISSION_DOWNLOAD

    def _on_exit(self):
        return self._next_state
