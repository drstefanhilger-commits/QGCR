# === PFAD-B FULL FILE: QGCR/states/mission/subfsms/mission_upload_fsm.py ===

from QGCR.states.base_fsm import BaseFSM
from QGCR.states.mission.mission_substate import MissionSubState


class MissionUploadFSM(BaseFSM):
    """
    MISSION_UPLOAD:
    - Simulierter Upload-Vorgang (Mockup)
    - Kein echter MAVLink-Upload
    - Nach Abschluss → MISSION_VALIDATE
    """

    def __init__(self, model):
        super().__init__(model, MissionSubState.MISSION_UPLOAD)
        self._progress = 0
        self._done = False
        self._next_state = MissionSubState.MISSION_UPLOAD

    # ------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------
    def _on_enter(self):
        self._progress = 0
        self._done = False

        try:
            self.model.queue_registry.require("gui").push(
                ("status", "Mission: UPLOAD gestartet")
            )
        except Exception:
            pass

    def _on_during(self):
        """
        MOCKUP-Upload:
        - zählt progress hoch
        - nach Erreichen von 100% → MISSION_VALIDATE
        """

        # Bereits abgeschlossen?
        if self._done:
            self._next_state = MissionSubState.MISSION_VALIDATE
            return

        # Fortschritt simulieren
        self._progress += 5

        try:
            self.model.queue_registry.require("gui").push(
                ("status", f"Mission: UPLOAD {self._progress}%")
            )
        except Exception:
            pass

        # Fertig?
        if self._progress >= 100:
            self._done = True
            try:
                self.model.queue_registry.require("gui").push(
                    ("status", "Mission: UPLOAD abgeschlossen")
                )
            except Exception:
                pass

            self._next_state = MissionSubState.MISSION_VALIDATE
            return

        # Kein Substate-Wechsel
        self._next_state = MissionSubState.MISSION_UPLOAD

    def _on_exit(self):
        return self._next_state
